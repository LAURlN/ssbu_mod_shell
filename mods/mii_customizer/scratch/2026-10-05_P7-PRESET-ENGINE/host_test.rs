//! Host-side unit tests for plugin/src/preset.rs, loadout.rs and logic.rs (the pure part of
//! the 0.3.0 preset build). Built and run by run_host_test.sh with the host rustc; no
//! skyline toolchain involved. The three files are compiled unchanged.
#![allow(dead_code)]

#[path = "../../plugin/src/loadout.rs"]
mod loadout;
#[path = "../../plugin/src/logic.rs"]
mod logic;
#[path = "../../plugin/src/preset.rs"]
mod preset;

use loadout as lo;
use loadout::{Src, Store, Table};
use logic::*;
use preset as pr;
use preset::Presets;

const GUNNER: i32 = 0x4a;
const W: u64 = 0x0607cd5541; // weight
const WS: u64 = 0x0ee2ec2860; // walk_speed_max
/// The ten field hashes of tools/stat-presets/stat_fields.txt, in that order.
const TEN: [u64; 10] = [
    0x0607cd5541, 0x0ee2ec2860, 0x0d5aaabf9b, 0x0adec47ea3, 0x1220fc2660, 0x12ec5626fe, 0x0ba18057d9, 0x0f71f4d4f8,
    0x06a0d82dad, 0x0cc9d2f2da,
];

fn mod_file(rel: &str) -> Vec<u8> {
    std::fs::read(format!("{}/{}", env!("MC_MOD_DIR"), rel)).unwrap()
}

fn text<const N: usize>(b: &LineBuf<N>) -> String {
    String::from_utf8(b.as_bytes().to_vec()).unwrap()
}

fn rng(seed: u64) -> impl FnMut() -> u64 {
    let mut s = seed;
    move || {
        s ^= s << 13;
        s ^= s >> 7;
        s ^= s << 17;
        s
    }
}

// ---------------------------------------------------------------- preset helpers

fn new_presets() -> Box<Presets> {
    let p = Box::new(Presets::new());
    p.init_named();
    p
}

fn pfile(body: &str) -> Vec<u8> {
    format!("mc_presets 1\n{body}").into_bytes()
}

fn pload(body: &str) -> (Box<Presets>, pr::Report) {
    let p = new_presets();
    let r = pr::parse(&pfile(body), &p);
    (p, r)
}

fn pname(p: &Presets, i: usize) -> String {
    let mut buf = [0u8; pr::NAME_BUF];
    let len = p.name(i, &mut buf);
    String::from_utf8(buf[..len].to_vec()).unwrap()
}

/// Value of preset `name` for field hash `hash`.
fn pval(p: &Presets, name: &str, hash: u64) -> Option<f32> {
    p.value(p.find_name(name.as_bytes())?, p.fields.find(hash)?)
}

/// The one rejected line of a preset file body: (line number, reason).
fn p_one_reject(body: &str) -> (u32, pr::Reject) {
    let (_, r) = pload(body);
    assert_eq!(r.state, pr::FileState::Ok, "{body:?}");
    assert_eq!(r.rejected, 1, "{body:?}");
    assert_eq!(r.rejects().len(), 1);
    r.rejects()[0]
}

fn synthetic() -> Box<Presets> {
    let p = new_presets();
    let r = pr::parse(&mod_file("scratch/2026-10-05_P7-PRESET-ENGINE/synthetic_presets.txt"), &p);
    assert_eq!((r.state, r.presets, r.fields, r.rejected, r.skipped), (pr::FileState::Ok, 3, 23, 0, 0));
    p
}

// ---------------------------------------------------------------- preset file

#[test]
fn preset_contract_constants() {
    assert_eq!(pr::VERSION_LINE, "mc_presets 1");
    assert_eq!(pr::MAX_FILE, 512 * 1024);
    assert_eq!(pr::MAX_PRESETS, 128);
    assert_eq!(pr::MAX_PRESET_FIELDS, 48);
    assert_eq!(pr::MAX_FILE_HASHES, 48);
    assert_eq!(pr::NAME_MAX, 31);
    assert_eq!(pr::REJECT_LOG_LIMIT, 32);
    assert_eq!(pr::FIELDS, 50);
    assert_eq!(pr::NAMED_HASHES, [W, WS]);
    assert!(pr::HASH_SLOTS.is_power_of_two() && pr::HASH_SLOTS >= 5 * pr::FIELDS);
    assert!(pr::FIELDS <= 64, "field sets are u64 bit masks");
}

#[test]
fn synthetic_preset_file() {
    let p = synthetic();
    assert_eq!(p.len(), 3);
    assert_eq!((pname(&p, 0), pname(&p, 1), pname(&p, 2)), ("zz_synth_fast".into(), "zz_synth_heavy".into(), "zz_synth_partial".into()));
    assert_eq!((p.kind(0), p.kind(1), p.kind(2), p.kind(3)), (0xa1, 0xa2, 0xa3, 0));
    assert_eq!(p.file_hashes(), 10);
    assert_eq!(p.fields.len(), 10);
    // field index = order of first appearance, the two named keys first
    for (i, h) in TEN.iter().enumerate() {
        assert_eq!(p.fields.find(*h), Some(i));
        assert_eq!(p.fields.hash_of(i), *h);
    }
    assert_eq!(p.fields.hash_of(10), 0);
    assert_eq!((p.field_count(0), p.field_count(1), p.field_count(2), p.field_count(3)), (10, 10, 3, 0));
    assert_eq!(pval(&p, "zz_synth_fast", W), Some(70.0));
    assert_eq!(pval(&p, "zz_synth_fast", TEN[7]), Some(0.08));
    assert_eq!(pval(&p, "zz_synth_heavy", W), Some(135.0));
    assert_eq!(pval(&p, "zz_synth_heavy", TEN[9]), Some(0.9));
    assert_eq!(pval(&p, "zz_synth_partial", W), Some(999.5));
    assert_eq!(pval(&p, "zz_synth_partial", WS), None);
    assert_eq!(pval(&p, "zz_synth_partial", TEN[8]), Some(12.5));
    assert_eq!(p.find_name(b"zz_synth"), None);
    assert_eq!(p.find_name(b"zz_synth_fast_"), None);
    assert_eq!(p.find_name(b""), None);
    assert_eq!(p.value(3, 0), None);
    assert_eq!(p.value(0, 10), None);
    assert_eq!(p.value(0, 50), None);
    assert_eq!(p.value(0, usize::MAX), None);
}

#[test]
fn preset_well_formed_variants() {
    let (p, r) = pload(
        "# comment\n\n\t \nfighter  a\t0x00000000AB   # trailing\r\n0x0607CD5541\t98 # c\n  0x0000000111 -1.5\n# caf\u{e9} \u{a0}\nfighter b_2 0xffffffffff\n0x0000000111 0",
    );
    assert_eq!((r.state, r.lines, r.presets, r.fields, r.rejected, r.skipped), (pr::FileState::Ok, 10, 2, 3, 0, 0));
    assert_eq!(p.kind(0), 0xab);
    assert_eq!(p.kind(1), 0xff_ffff_ffff);
    assert_eq!(pval(&p, "a", W), Some(98.0));
    assert_eq!(pval(&p, "a", 0x111), Some(-1.5));
    assert_eq!(pval(&p, "b_2", 0x111), Some(0.0));
    assert_eq!(pval(&p, "b_2", W), None);
    // bytes that are not UTF-8 are harmless in a comment
    let mut bytes = pfile("fighter a 0x0000000001\n");
    bytes.extend_from_slice(b"# \xff\xfe\n0x0000000111 2 # \xff\n");
    let p = new_presets();
    let r = pr::parse(&bytes, &p);
    assert_eq!((r.fields, r.rejected), (1, 0));
    // an empty preset is a preset; a file with the version line only has none
    let (p, r) = pload("fighter empty 0x0000000001\n");
    assert_eq!((p.len(), r.presets, p.field_count(0), p.file_hashes()), (1, 1, 0, 0));
    for bytes in [&b"mc_presets 1"[..], b"mc_presets 1\n", b"mc_presets 1\r\n"] {
        let p = new_presets();
        let r = pr::parse(bytes, &p);
        assert_eq!((r.state, r.lines, p.len(), p.fields.len()), (pr::FileState::Ok, 1, 0, 2));
    }
}

#[test]
fn preset_values_are_finite_and_not_range_limited() {
    let (p, r) = pload("fighter a 0x0000000001\n0x0607cd5541 0\n0x0ee2ec2860 -250.5\n0x0000000003 999999999\n0x0000000004 0.000001\n");
    assert_eq!((r.fields, r.rejected), (4, 0));
    assert_eq!(pval(&p, "a", W), Some(0.0));
    assert_eq!(pval(&p, "a", WS), Some(-250.5));
    assert_eq!(pval(&p, "a", 3), Some(999999999.0));
    assert_eq!(pval(&p, "a", 4), Some(0.000001));
    for v in ["abc", "1e2", "1E2", "inf", "-inf", "nan", "NaN", "0x64", "100.", ".5", "1.2.3", "1,5", "+100", "--1", "-", "1234567890123456789", "1000000000000000000000000", "1\u{a0}"] {
        assert_eq!(p_one_reject(&format!("fighter a 0x0000000001\n0x0000000003 {v}\n")), (3, pr::Reject::BadValue), "{v}");
    }
    // every stored value is finite: the parser cannot produce anything else
    for field in 0..pr::FIELDS {
        if let Some(v) = p.value(0, field) {
            assert!(v.is_finite());
        }
    }
}

#[test]
fn preset_bad_first_line_gives_no_presets() {
    for head in [
        "", "\n", "mc_presets 2\n", "mc_presets 1 \n", " mc_presets 1\n", "mc_presets  1\n", "mc_presets\n", "MC_PRESETS 1\n",
        "mc_presets 1.0\n", "mc_presets 10\n", "# c\nmc_presets 1\n", "fighter a 0x0000000001\n", "mc_presets 1 # v\n",
        "mc_presets\t1\n", "mc_loadouts 1\n", "mc_loadouts 2\n",
    ] {
        let bytes = format!("{head}fighter a 0x0000000001\n0x0607cd5541 98\n0x0000000111 2\n").into_bytes();
        let p = new_presets();
        let r = pr::parse(&bytes, &p);
        assert_eq!(r.state, pr::FileState::BadVersionLine, "{head:?}");
        assert_eq!((p.len(), r.presets, r.fields, p.file_hashes()), (0, 0, 0, 0), "{head:?}");
        // the two named keys stay known, nothing else is
        assert_eq!((p.fields.len(), p.fields.find(W), p.fields.find(WS), p.fields.find(0x111)), (2, Some(0), Some(1), None));
    }
    let p = new_presets();
    let r = pr::parse(b"\xef\xbb\xbfmc_presets 1\nfighter a 0x0000000001\n", &p);
    assert_eq!((r.state, p.len()), (pr::FileState::BadVersionLineBom, 0));
    let p = new_presets();
    let r = pr::parse(b"\xffmc_presets 1\nfighter a 0x0000000001\n", &p);
    assert_eq!((r.state, p.len()), (pr::FileState::BadVersionLine, 0));
    assert_eq!(pr::FileState::BadVersionLine.name(), "bad_version_line");
}

#[test]
fn preset_file_size_limit() {
    let mut bytes = pfile("fighter a 0x0000000001\n0x0000000111 2\n");
    bytes.resize(pr::MAX_FILE, b'\n');
    let p = new_presets();
    let r = pr::parse(&bytes, &p);
    assert_eq!((r.state, p.len(), pval(&p, "a", 0x111)), (pr::FileState::Ok, 1, Some(2.0)));
    bytes.push(b'\n');
    assert_eq!(bytes.len(), 512 * 1024 + 1);
    let p = new_presets();
    let r = pr::parse(&bytes, &p);
    assert_eq!((r.state, p.len(), r.presets, p.fields.len()), (pr::FileState::TooLarge, 0, 0, 2));
}

#[test]
fn preset_fighter_line_rules() {
    // names
    let long31 = "a".repeat(31);
    let long32 = "a".repeat(32);
    let (p, r) = pload(&format!("fighter {long31} 0x0000000001\nfighter 0_9 0x0000000002\nfighter _ 0x0000000003\n"));
    assert_eq!((r.presets, r.rejected), (3, 0));
    assert_eq!(pname(&p, 0), long31);
    assert_eq!(p.find_name(long31.as_bytes()), Some(0));
    for name in [long32.as_str(), "Mario", "mario-2", "mario.x", "mari\u{f6}", "a/b", "a=b"] {
        assert_eq!(p_one_reject(&format!("fighter {name} 0x0000000001\n")), (2, pr::Reject::BadName), "{name}");
    }
    // kind hashes
    for kind in ["0x000000001", "0x00000000001", "0000000001", "0X0000000001", "0x000000000g", "x0000000001", "0x", "12"] {
        assert_eq!(p_one_reject(&format!("fighter a {kind}\n")), (2, pr::Reject::BadHash), "{kind}");
    }
    assert_eq!(pr::parse_hash(b"0x0607cd5541"), Some(W));
    assert_eq!(pr::parse_hash(b"0x0607CD5541"), Some(W));
    assert_eq!(pr::parse_hash(b"0x0000000000"), Some(0));
    // field counts
    for line in ["fighter", "fighter a", "fighter a 0x0000000001 x", "fighter a 0x0000000001 0x0000000002"] {
        assert_eq!(p_one_reject(&format!("{line}\n")), (2, pr::Reject::FieldCount), "{line}");
    }
    assert_eq!(p_one_reject("Fighter a 0x0000000001\n").1, pr::Reject::FieldCount); // three fields, not a `fighter` line
    // `fighter` is not reserved as a name
    let (p, r) = pload("fighter fighter 0x0000000001\n");
    assert_eq!((r.presets, pname(&p, 0)), (1, "fighter".into()));
}

#[test]
fn preset_rejected_fighter_line_does_not_leak_into_the_previous_preset() {
    let (p, r) = pload(
        "fighter a 0x0000000001\n0x0000000111 1\nfighter B 0x0000000002\n0x0000000111 2\n0x0000000222 2\nfighter c 0x0000000003\n0x0000000333 3\n",
    );
    assert_eq!((r.presets, r.fields, r.rejected, r.skipped), (2, 2, 1, 2));
    assert_eq!(r.rejects(), &[(4, pr::Reject::BadName)]);
    assert_eq!((pname(&p, 0), pname(&p, 1)), ("a".into(), "c".into()));
    assert_eq!(pval(&p, "a", 0x111), Some(1.0));
    assert_eq!(p.field_count(0), 1);
    assert_eq!(pval(&p, "c", 0x333), Some(3.0));
    // the skipped preset's hash 0x222 never became a known field
    assert_eq!(p.fields.find(0x222), None);
    assert_eq!(p.file_hashes(), 2);
}

#[test]
fn preset_duplicate_name_rejects_the_whole_preset() {
    let (p, r) = pload(
        "fighter a 0x0000000001\n0x0000000111 1\nfighter b 0x0000000002\n0x0000000111 2\nfighter a 0x0000000009\n0x0000000111 9\n0x0000000222 9\nfighter c 0x0000000003\n0x0000000111 3\n",
    );
    assert_eq!((r.presets, r.fields, r.rejected, r.skipped), (3, 3, 1, 2));
    assert_eq!(r.rejects(), &[(6, pr::Reject::DupName)]);
    assert_eq!(p.len(), 3);
    assert_eq!((p.kind(0), pval(&p, "a", 0x111), p.field_count(0)), (1, Some(1.0), 1));
    assert_eq!(pval(&p, "b", 0x111), Some(2.0));
    assert_eq!(pval(&p, "c", 0x111), Some(3.0));
    assert_eq!(p.fields.find(0x222), None);
}

#[test]
fn preset_field_line_rules() {
    // a field line before any `fighter` line
    let (p, r) = pload("0x0000000111 1\n0x0000000222 2\nfighter a 0x0000000001\n0x0000000111 3\n");
    assert_eq!((r.fields, r.rejected), (1, 2));
    assert_eq!(r.rejects(), &[(2, pr::Reject::NoPreset), (3, pr::Reject::NoPreset)]);
    assert_eq!((pval(&p, "a", 0x111), p.fields.find(0x222)), (Some(3.0), None));
    // field hashes
    for hash in ["0x000000111", "0x00000000111", "0000000111", "0X0000000111", "0x000000011g", "0x0000000000", "weight"] {
        assert_eq!(p_one_reject(&format!("fighter a 0x0000000001\n{hash} 1\n")), (3, pr::Reject::BadHash), "{hash}");
    }
    // field counts
    for line in ["0x0000000111", "0x0000000111 1 2", "0x0000000111=1", "0x0000000111 #1"] {
        assert_eq!(p_one_reject(&format!("fighter a 0x0000000001\n{line}\n")), (3, pr::Reject::FieldCount), "{line}");
    }
    // a repeated field inside one preset: the first value stays
    let (p, r) = pload("fighter a 0x0000000001\n0x0000000111 1\n0x0000000111 2\n0x0607cd5541 98\n0x0607CD5541 99\nfighter b 0x0000000002\n0x0000000111 5\n");
    assert_eq!(r.rejects(), &[(4, pr::Reject::DupField), (6, pr::Reject::DupField)]);
    assert_eq!((pval(&p, "a", 0x111), pval(&p, "a", W), pval(&p, "b", 0x111)), (Some(1.0), Some(98.0), Some(5.0)));
    assert_eq!((r.fields, p.field_count(0)), (3, 2));
    // a bad line inside a preset does not end the preset
    let (p, r) = pload("fighter a 0x0000000001\n0x0000000111 1\ngarbage\n0x0000000222 2\n");
    assert_eq!((r.fields, r.rejected, p.field_count(0)), (2, 1, 2));
}

#[test]
fn preset_limit_128_presets() {
    let mut body = String::new();
    for i in 0..130 {
        body += &format!("fighter p{i} 0x{:010x}\n0x0000000111 {i}\n", i + 1);
    }
    let (p, r) = pload(&body);
    assert_eq!((p.len(), r.presets, r.fields, r.rejected, r.skipped), (128, 128, 128, 2, 2));
    assert_eq!(r.rejects(), &[(2 * 128 + 2, pr::Reject::TooManyPresets), (2 * 129 + 2, pr::Reject::TooManyPresets)]);
    assert_eq!(pval(&p, "p127", 0x111), Some(127.0));
    assert_eq!((p.find_name(b"p128"), p.find_name(b"p129")), (None, None));
    assert_eq!((p.kind(127), p.kind(128)), (128, 0));
}

#[test]
fn preset_limit_48_distinct_hashes() {
    // 48 distinct hashes, none of them a named key: table = 2 named + 48 = 50 = full
    let mut body = String::from("fighter a 0x0000000001\n");
    for i in 0..48 {
        body += &format!("0x{:010x} {i}\n", 0x1000 + i);
    }
    let (p, r) = pload(&body);
    assert_eq!((r.fields, r.rejected, p.file_hashes(), p.fields.len(), p.field_count(0)), (48, 0, 48, 50, 48));
    assert_eq!(pval(&p, "a", 0x1000 + 47), Some(47.0));
    // a 49th field line of a full preset is rejected as such (also when its hash is new);
    // a 49th distinct hash is rejected wherever it appears; known hashes still work
    body += "0x0000002000 1\nfighter b 0x0000000002\n0x0000002001 1\n0x0000001000 7\n0x0607cd5541 98\n";
    let (p, r) = pload(&body);
    assert_eq!(r.rejects(), &[(51, pr::Reject::TooManyFields), (53, pr::Reject::TooManyHashes), (55, pr::Reject::TooManyHashes)]);
    assert_eq!((p.file_hashes(), p.fields.len()), (48, 50));
    assert_eq!((p.fields.find(0x2000), p.fields.find(0x2001)), (None, None));
    assert_eq!(pval(&p, "b", 0x1000), Some(7.0));
    // the named keys count as file hashes when the file uses them: 2 + 46 others = 48
    let mut body = String::from("fighter a 0x0000000001\n0x0607cd5541 98\n0x0ee2ec2860 1\n");
    for i in 0..46 {
        body += &format!("0x{:010x} {i}\n", 0x1000 + i);
    }
    body += "0x0000002000 1\nfighter b 0x0000000002\n0x0000002000 1\n0x0ee2ec2860 2\n";
    let (p, r) = pload(&body);
    assert_eq!((r.fields, p.file_hashes(), p.fields.len()), (49, 48, 48));
    assert_eq!(r.rejects(), &[(51, pr::Reject::TooManyFields), (53, pr::Reject::TooManyHashes)]);
    assert_eq!(pval(&p, "b", WS), Some(2.0));
    // every stored hash is found, with the index it was given
    for field in 0..p.fields.len() {
        assert_eq!(p.fields.find(p.fields.hash_of(field)), Some(field));
    }
}

#[test]
fn preset_reject_log_is_bounded_but_counts_everything() {
    let mut body = String::from("fighter a 0x0000000001\n");
    for _ in 0..100 {
        body += "zzz\n";
    }
    body += "0x0000000111 1\n";
    let (p, r) = pload(&body);
    assert_eq!((r.rejected, r.rejects().len(), r.fields), (100, 32, 1));
    assert_eq!(r.rejects()[31], (34, pr::Reject::FieldCount));
    assert_eq!(pval(&p, "a", 0x111), Some(1.0));
    let all = [
        pr::Reject::FieldCount, pr::Reject::BadName, pr::Reject::BadHash, pr::Reject::DupName, pr::Reject::TooManyPresets,
        pr::Reject::NoPreset, pr::Reject::DupField, pr::Reject::TooManyFields, pr::Reject::TooManyHashes, pr::Reject::BadValue,
    ];
    let mut names: Vec<&str> = all.iter().map(|w| w.name()).collect();
    names.sort();
    names.dedup();
    assert_eq!(names.len(), all.len());
}

#[test]
fn preset_arbitrary_bytes_never_panic() {
    let mut next = rng(0x2545_f491_4f6c_dd1d);
    let alphabet = b"mc_presets 1\n\n\r\t #0x0123456789abcdefABCDEF fighter zz_ .-+\xff\xc3\xa9";
    let words: [&[u8]; 6] = [b"fighter ", b"0x0607cd5541 ", b"0x0000000111 ", b"\n", b"aa 0x0000000001\n", b"1.5\n"];
    for round in 0..3000 {
        let len = (next() % 600) as usize;
        let mut bytes = if round % 2 == 0 { b"mc_presets 1\n".to_vec() } else { Vec::new() };
        for _ in 0..len {
            if next() % 4 == 0 {
                bytes.extend_from_slice(words[(next() % 6) as usize]);
            } else {
                bytes.push(alphabet[(next() % alphabet.len() as u64) as usize]);
            }
        }
        let p = new_presets();
        let r = pr::parse(&bytes, &p);
        assert!(p.len() <= pr::MAX_PRESETS && p.fields.len() <= pr::FIELDS && p.file_hashes() as usize <= pr::MAX_FILE_HASHES);
        assert_eq!(p.len() as u32, r.presets);
        if r.state != pr::FileState::Ok {
            assert_eq!((p.len(), p.fields.len()), (0, 2));
        }
        let mut total = 0;
        for i in 0..p.len() {
            assert!(pr::valid_name(pname(&p, i).as_bytes()));
            assert_eq!(p.find_name(pname(&p, i).as_bytes()), Some(i), "names are unique");
            total += p.field_count(i);
            for field in 0..pr::FIELDS {
                if let Some(v) = p.value(i, field) {
                    assert!(v.is_finite() && field < p.fields.len());
                }
            }
        }
        assert_eq!(total, r.fields);
    }
}

// ---------------------------------------------------------------- field hash table

#[test]
fn field_table_lookup() {
    let t = pr::FieldTable::new();
    // empty: nothing is found and nothing is examined
    assert_eq!((t.len(), t.probe_max(), t.find(W), t.find(0), t.find(u64::MAX)), (0, 0, None, None, None));
    assert_eq!(t.insert(0), None);
    assert_eq!(t.insert(W), Some(0));
    assert_eq!(t.insert(WS), Some(1));
    assert_eq!(t.insert(W), Some(0)); // again: same index, nothing added
    assert_eq!((t.len(), t.find(W), t.find(WS), t.find(0)), (2, Some(0), Some(1), None));
    assert_eq!((t.hash_of(0), t.hash_of(1), t.hash_of(2)), (W, WS, 0));
    // neighbours of a stored hash are not found
    for d in 1..2000u64 {
        assert_eq!(t.find(W + d), None);
        assert_eq!(t.find(W - d), None);
        assert_eq!(t.find(W ^ (d << 20)), None);
    }
    // the ten real hashes
    let t = pr::FieldTable::new();
    for (i, h) in TEN.iter().enumerate() {
        assert_eq!(t.insert(*h), Some(i));
    }
    for (i, h) in TEN.iter().enumerate() {
        assert_eq!(t.find(*h), Some(i));
    }
    assert!(t.probe_max() >= 1 && t.probe_max() <= 10);
    let mut next = rng(99);
    for _ in 0..200_000 {
        let h = next() & 0xff_ffff_ffff;
        assert_eq!(t.find(h), TEN.iter().position(|x| *x == h));
    }
}

#[test]
fn field_table_worst_case_is_bounded_by_the_number_of_fields() {
    assert!((0..100_000u64).all(|h| pr::home_slot(h.wrapping_mul(0x1234_5678_9abc_def1)) < pr::HASH_SLOTS));
    // 50 hashes that all want the same slot, and one more with that home slot that is absent
    let home = pr::home_slot(W);
    let mut same: Vec<u64> = (1..u64::MAX).filter(|h| pr::home_slot(*h) == home).take(51).collect();
    let absent = same.pop().unwrap();
    let t = pr::FieldTable::new();
    for (i, h) in same.iter().enumerate() {
        assert_eq!(t.insert(*h), Some(i));
    }
    assert_eq!((t.len(), t.probe_max()), (50, 50));
    for (i, h) in same.iter().enumerate() {
        assert_eq!(t.find(*h), Some(i));
    }
    assert_eq!(t.find(absent), None);
    assert_eq!(t.find(0), None);
    // full: a 51st hash is refused and changes nothing
    assert_eq!(t.insert(absent), None);
    assert_eq!((t.len(), t.probe_max(), t.find(absent)), (50, 50, None));
    // two hashes that differ only above bit 31 (hash40 keeps the name length there) and probe
    // the same slot: the lookup must compare all 64 bits
    let (stored, twin) = (1..u64::MAX)
        .find_map(|low| {
            let mut by_slot = [u64::MAX; pr::HASH_SLOTS];
            (0..256u64).find_map(|high| {
                let h = (high << 32) | low;
                let slot = pr::home_slot(h);
                let other = std::mem::replace(&mut by_slot[slot], h);
                (other != u64::MAX).then_some((other, h))
            })
        })
        .unwrap();
    assert_eq!((stored as u32, pr::home_slot(stored)), (twin as u32, pr::home_slot(twin)));
    assert_ne!(stored, twin);
    let t = pr::FieldTable::new();
    assert_eq!(t.insert(stored), Some(0));
    assert_eq!((t.find(stored), t.find(twin)), (Some(0), None));
    // a cluster that wraps around the end of the table
    let last: Vec<u64> = (1..u64::MAX).filter(|h| pr::home_slot(*h) == pr::HASH_SLOTS - 1).take(5).collect();
    let t = pr::FieldTable::new();
    for (i, h) in last.iter().enumerate() {
        assert_eq!(t.insert(*h), Some(i));
    }
    for (i, h) in last.iter().enumerate() {
        assert_eq!(t.find(*h), Some(i));
    }
    assert_eq!(t.probe_max(), 5);
}

// ---------------------------------------------------------------- loadout file

fn lfile(version: u8, body: &str) -> Vec<u8> {
    format!("mc_loadouts {version}\n{body}").into_bytes()
}

fn lparse(version: u8, body: &str, p: &Presets) -> (Box<Table>, lo::Report) {
    lo::parse(&lfile(version, body), p)
}

fn l_one_reject(version: u8, body: &str) -> lo::Reject {
    let p = synthetic();
    let (table, report) = lparse(version, body, &p);
    assert_eq!(report.state, lo::FileState::Ok, "{body:?}");
    assert_eq!(table.len(), 0, "{body:?}");
    assert_eq!(report.accepted, 0, "{body:?}");
    assert_eq!(report.rejected, 1, "{body:?}");
    assert_eq!(report.rejects().len(), 1);
    assert_eq!(report.rejects()[0].0, 2, "line number of {body:?}");
    report.rejects()[0].1
}

#[test]
fn loadout_contract_constants() {
    assert_eq!(lo::VERSION_LINE_1, "mc_loadouts 1");
    assert_eq!(lo::VERSION_LINE_2, "mc_loadouts 2");
    assert_eq!(lo::MAX_FILE, 16384);
    assert_eq!(lo::MAX_IDS, 32);
    assert_eq!(lo::REJECT_LOG_LIMIT, 32);
    assert_eq!(lo::KEY_NAMES, ["weight", "walk_speed_max"]);
    assert_eq!(lo::PRESET_KEY, "preset");
    assert_eq!(lo::RANGES, [(60.0, 140.0), (0.5, 2.0)]);
    // key index == field index of the key's hash, so a key cannot be applied to another hash
    let p = new_presets();
    assert_eq!(lo::KEYS, pr::NAMED);
    assert_eq!(p.fields.find(W), lo::key_index("weight"));
    assert_eq!(p.fields.find(WS), lo::key_index("walk_speed_max"));
    assert_eq!(lo::key_index("preset"), None);
    assert_eq!((Src::Explicit.name(), Src::Preset.name()), ("explicit", "preset"));
}

#[test]
fn loadout_version_1_file_of_0_2_0_reads_as_before() {
    let bytes = mod_file("builds/0.2.0-override/example/loadouts.txt");
    for p in [new_presets(), synthetic()] {
        let (table, report) = lo::parse(&bytes, &p);
        assert_eq!((report.state, report.version), (lo::FileState::Ok, 1));
        assert_eq!((report.accepted, report.preset_lines, report.replaced, report.rejected), (2, 0, 0, 0));
        assert_eq!(table.len(), 1);
        assert_eq!((table.get(0xf589, 0), table.get(0xf589, 1), table.preset(0xf589)), (Some(130.0), Some(1.6), None));
        assert_eq!((table.get(0xf58b, 0), table.get(0xf58b, 1)), (None, None));
    }
}

#[test]
fn loadout_delivered_example_file() {
    let bytes = mod_file("builds/0.3.0-presets/example/loadouts.txt");
    assert!(bytes.len() <= lo::MAX_FILE && !bytes.contains(&b'\r') && bytes.is_ascii());
    // as delivered: the placeholder is not a preset, so nothing is active
    let p = synthetic();
    let (table, report) = lo::parse(&bytes, &p);
    assert_eq!((report.state, report.version, report.accepted, report.rejected, table.len()), (lo::FileState::Ok, 2, 0, 1, 0));
    assert_eq!(report.rejects()[0].1, lo::Reject::UnknownPreset);
    // with the placeholder replaced by an existing name: one Mii, one preset, nothing else
    let text = String::from_utf8(bytes).unwrap();
    assert_eq!(text.matches("replace_with_preset_name").count(), 1);
    let (table, report) = lo::parse(text.replace("replace_with_preset_name", "zz_synth_fast").as_bytes(), &p);
    assert_eq!((report.accepted, report.preset_lines, report.rejected, table.len()), (1, 1, 0, 1));
    assert_eq!((table.preset(0xf589), table.get(0xf589, 0), table.get(0xf589, 1), table.preset(0xf58b)), (Some(0), None, None, None));
}

#[test]
fn loadout_well_formed_version_2() {
    let p = synthetic();
    let (table, report) = lparse(
        2,
        "# comment line\n\n0000f589 preset zz_synth_fast\n0000F589\tweight\t130.0   # trailing comment\n  \t \n  0000f58b   preset   zz_synth_partial\r\n0000f58c walk_speed_max 0.5",
        &p,
    );
    assert_eq!((report.state, report.version, report.lines), (lo::FileState::Ok, 2, 8));
    assert_eq!((report.accepted, report.preset_lines, report.replaced, report.rejected, report.cleared), (4, 2, 0, 0, 0));
    assert_eq!(table.len(), 3);
    assert_eq!((table.preset(0xf589), table.get(0xf589, 0), table.get(0xf589, 1)), (Some(0), Some(130.0), None));
    assert_eq!((table.preset(0xf58b), table.get(0xf58b, 0)), (Some(2), None));
    assert_eq!((table.preset(0xf58c), table.get(0xf58c, 1)), (None, Some(0.5)));
    // version line only
    for bytes in [&b"mc_loadouts 2"[..], b"mc_loadouts 2\n", b"mc_loadouts 1", b"mc_loadouts 1\r\n"] {
        let (table, report) = lo::parse(bytes, &p);
        assert_eq!((report.state, report.lines, table.len()), (lo::FileState::Ok, 1, 0));
    }
}

#[test]
fn loadout_preset_key_exists_in_version_2_only() {
    let p = synthetic();
    let (table, report) = lparse(1, "0000f589 preset zz_synth_fast\n0000f589 weight 130\n", &p);
    assert_eq!((report.version, report.accepted, report.preset_lines), (1, 1, 0));
    assert_eq!(report.rejects(), &[(2, lo::Reject::UnknownKey)]);
    assert_eq!((table.preset(0xf589), table.get(0xf589, 0)), (None, Some(130.0)));
    assert_eq!(l_one_reject(1, "0000f589 preset zz_synth_fast\n"), lo::Reject::UnknownKey);
    let (table, report) = lparse(2, "0000f589 preset zz_synth_fast\n", &p);
    assert_eq!((report.accepted, report.rejected, table.preset(0xf589)), (1, 0, Some(0)));
    // the key is exactly `preset`
    for key in ["Preset", "presets", "preset_", "PRESET"] {
        assert_eq!(l_one_reject(2, &format!("0000f589 {key} zz_synth_fast\n")), lo::Reject::UnknownKey, "{key}");
    }
}

#[test]
fn loadout_unknown_preset_is_rejected_and_the_mii_has_no_preset() {
    let p = synthetic();
    assert_eq!(l_one_reject(2, "0000f589 preset mario\n"), lo::Reject::UnknownPreset);
    assert_eq!(l_one_reject(2, "0000f589 preset zz_synth\n"), lo::Reject::UnknownPreset);
    assert_eq!(l_one_reject(2, "0000f589 preset zz_synth_fastx\n"), lo::Reject::UnknownPreset);
    for name in ["ZZ_SYNTH_FAST", "zz-synth-fast", "130.0", "zz_synth_fast!", &"a".repeat(32)] {
        let why = l_one_reject(2, &format!("0000f589 preset {name}\n"));
        assert!(why == lo::Reject::BadName || (name == "130.0" && why == lo::Reject::BadName), "{name}: {why:?}");
    }
    // no preset file at all: every preset line is unknown, explicit lines still work
    let none = new_presets();
    let (table, report) = lparse(2, "0000f589 preset zz_synth_fast\n0000f589 weight 130\n", &none);
    assert_eq!(report.rejects(), &[(2, lo::Reject::UnknownPreset)]);
    assert_eq!((table.len(), table.preset(0xf589), table.get(0xf589, 0)), (1, None, Some(130.0)));
    // a later bad preset line takes an earlier preset of that ID away ...
    let (table, report) = lparse(2, "0000f589 preset zz_synth_fast\n0000f58b preset zz_synth_heavy\n0000f589 preset nope\n", &p);
    assert_eq!((report.accepted, report.rejected, report.cleared), (2, 1, 1));
    assert_eq!(report.rejects(), &[(4, lo::Reject::UnknownPreset)]);
    // ... and an ID left without content is not in the table
    assert_eq!((table.len(), table.preset(0xf589), table.preset(0xf58b)), (1, None, Some(1)));
    assert_eq!(table.entries()[0].id, 0xf58b);
    // explicit values of that ID stay
    let (table, report) = lparse(2, "0000f589 weight 70\n0000f589 preset zz_synth_fast\n0000f589 preset NOPE\n0000f58b weight 61\n", &p);
    assert_eq!((report.cleared, table.len()), (1, 2));
    assert_eq!(report.rejects(), &[(4, lo::Reject::BadName)]);
    assert_eq!((table.preset(0xf589), table.get(0xf589, 0), table.get(0xf58b, 0)), (None, Some(70.0), Some(61.0)));
    assert_eq!((table.entries()[0].id, table.entries()[1].id), (0xf589, 0xf58b));
    // a bad preset line for an ID without preset clears nothing
    let (table, report) = lparse(2, "0000f589 weight 70\n0000f589 preset nope\n", &p);
    assert_eq!((report.cleared, table.len(), table.get(0xf589, 0)), (0, 1, Some(70.0)));
}

#[test]
fn loadout_bad_first_line_disables_everything() {
    let p = synthetic();
    for head in [
        "", "\n", "mc_loadouts 3\n", "mc_loadouts 0\n", "mc_loadouts 1 \n", " mc_loadouts 2\n", "mc_loadouts  2\n", "mc_loadouts\n",
        "MC_LOADOUTS 2\n", "mc_loadouts 2.0\n", "mc_loadouts 10\n", "mc_loadouts 12\n", "mc_loadouts 21\n", "# c\nmc_loadouts 2\n",
        "0000f589 weight 130\n", "mc_loadouts 2 # v\n", "mc_loadouts\t1\n", "mc_presets 1\n",
    ] {
        let bytes = format!("{head}0000f589 weight 130.0\n0000f589 preset zz_synth_fast\n").into_bytes();
        let (table, report) = lo::parse(&bytes, &p);
        assert_eq!(report.state, lo::FileState::BadVersionLine, "{head:?}");
        assert_eq!((table.len(), report.accepted, report.version), (0, 0, 0), "{head:?}");
        let store = Store::new();
        store.publish(&table);
        assert_eq!(store.resolve(0xf589, 0, &p), None);
    }
    let (table, report) = lo::parse(b"\xef\xbb\xbfmc_loadouts 2\n0000f589 weight 130.0\n", &p);
    assert_eq!((report.state, table.len()), (lo::FileState::BadVersionLineBom, 0));
    let (table, report) = lo::parse(b"\xffmc_loadouts 2\n0000f589 weight 130.0\n", &p);
    assert_eq!((report.state, table.len()), (lo::FileState::BadVersionLine, 0));
}

#[test]
fn loadout_file_size_limit_stays_16_kib() {
    let p = synthetic();
    for version in [1, 2] {
        let mut bytes = lfile(version, "0000f589 weight 130.0\n");
        bytes.resize(lo::MAX_FILE, b'\n');
        let (table, report) = lo::parse(&bytes, &p);
        assert_eq!((report.state, table.get(0xf589, 0)), (lo::FileState::Ok, Some(130.0)));
        bytes.push(b'\n');
        assert_eq!(bytes.len(), 16385);
        let (table, report) = lo::parse(&bytes, &p);
        assert_eq!((report.state, table.len(), report.accepted), (lo::FileState::TooLarge, 0, 0));
    }
}

#[test]
fn loadout_rejected_ids_keys_and_field_counts() {
    for version in [1, 2] {
        for id in ["f589", "0000f58", "0000f5890", "0x00f589", "0000f58g", "+000f589", "-000f589", "f589f589f"] {
            assert_eq!(l_one_reject(version, &format!("{id} weight 100\n")), lo::Reject::BadId, "{id}");
            if version == 2 {
                assert_eq!(l_one_reject(2, &format!("{id} preset zz_synth_fast\n")), lo::Reject::BadId, "{id}");
            }
        }
        assert_eq!(l_one_reject(version, "00000000 weight 100\n"), lo::Reject::ZeroId);
        for key in ["Weight", "weight_", "walk_speed", "walk_speed_max2", "dash_speed", "0", "jump", "0x0607cd5541"] {
            assert_eq!(l_one_reject(version, &format!("0000f589 {key} 100\n")), lo::Reject::UnknownKey, "{key}");
        }
        for line in ["0000f589", "0000f589 weight", "0000f589 weight 100 1", "weight", "0000f589 weight=100", "0000f589,weight,100", "0000 f589 weight 100", "0000f589 preset", "0000f589 preset a b"] {
            assert_eq!(l_one_reject(version, &format!("{line}\n")), lo::Reject::FieldCount, "{line}");
        }
        assert_eq!(l_one_reject(version, "0000f589 weight #100\n"), lo::Reject::FieldCount);
        assert_eq!(l_one_reject(version, "0000f589\u{a0}weight 100\n"), lo::Reject::FieldCount);
    }
    assert_eq!(l_one_reject(2, "00000000 preset zz_synth_fast\n"), lo::Reject::ZeroId);
    assert_eq!(lo::parse_id("ffffffff"), Ok(0xffff_ffff));
    assert_eq!(lo::parse_id("0000F589"), Ok(0xf589));
    assert_eq!(lo::parse_id("00000001"), Ok(1));
}

#[test]
fn loadout_rejected_values_and_ranges_as_in_0_2_0() {
    for version in [1, 2] {
        for v in [
            "abc", "1e2", "1E2", "inf", "-inf", "nan", "NaN", "infinity", "0x64", "100.", ".5", "1.2.3", "1,5", "+100", "--1", "-",
            "100f", "1_00", "١٠٠", "1234567890123456789", "0.0000000000000000001", "1000000000000000000000000",
        ] {
            assert_eq!(l_one_reject(version, &format!("0000f589 weight {v}\n")), lo::Reject::BadValue, "{v}");
        }
        for (key, v) in [
            ("weight", "59.999"), ("weight", "140.001"), ("weight", "0"), ("weight", "-100"), ("weight", "1000"),
            ("weight", "999999999999999999"), ("walk_speed_max", "0.499"), ("walk_speed_max", "2.001"),
            ("walk_speed_max", "0"), ("walk_speed_max", "-1.0"), ("walk_speed_max", "100"), ("weight", "1.6"),
        ] {
            assert_eq!(l_one_reject(version, &format!("0000f589 {key} {v}\n")), lo::Reject::OutOfRange, "{key} {v}");
        }
    }
    let p = new_presets();
    for (key, v, want) in [
        ("weight", "60", 60.0f32), ("weight", "60.0", 60.0), ("weight", "140", 140.0), ("weight", "140.000", 140.0),
        ("weight", "104.5", 104.5), ("weight", "0104", 104.0), ("walk_speed_max", "0.5", 0.5), ("walk_speed_max", "2", 2.0),
        ("walk_speed_max", "2.0", 2.0), ("walk_speed_max", "1.155", 1.155), ("walk_speed_max", "1.6", 1.6),
        ("walk_speed_max", "001.5230", 1.523),
    ] {
        let (table, report) = lparse(2, &format!("0000f589 {key} {v}\n"), &p);
        assert_eq!(report.rejected, 0, "{key} {v}");
        assert_eq!(table.get(0xf589, lo::key_index(key).unwrap()), Some(want), "{key} {v}");
    }
    assert_eq!(lo::parse_decimal("130.0"), Some(130.0));
    assert_eq!(lo::parse_decimal("-1.5"), Some(-1.5));
    assert_eq!(lo::parse_decimal("0.1"), Some(0.1));
    assert_eq!(lo::parse_decimal("123456789012345678"), Some(123456789012345678.0));
    assert_eq!(lo::parse_decimal(""), None);
    assert!(!lo::in_range(0, f32::NAN) && !lo::in_range(0, f32::INFINITY) && !lo::in_range(2, 1.0));
}

#[test]
fn loadout_non_utf8_line_is_ignored_alone() {
    let p = synthetic();
    let mut bytes = lfile(2, "0000f589 weight 130.0\n");
    bytes.extend_from_slice(b"0000f58b weight 1\xff0\n");
    bytes.extend_from_slice(b"# caf\xe9\n");
    bytes.extend_from_slice(b"0000f58b preset zz_synth_heavy\n");
    let (table, report) = lo::parse(&bytes, &p);
    assert_eq!((report.state, report.accepted, report.rejected), (lo::FileState::Ok, 2, 2));
    assert_eq!(report.rejects(), &[(3, lo::Reject::NonUtf8), (4, lo::Reject::NonUtf8)]);
    assert_eq!((table.get(0xf589, 0), table.get(0xf58b, 0), table.preset(0xf58b)), (Some(130.0), None, Some(1)));
}

#[test]
fn loadout_later_line_replaces_earlier_one() {
    let p = synthetic();
    let (table, report) = lparse(
        2,
        "0000f589 weight 130\n0000f589 walk_speed_max 1.6\n0000f589 weight 70\n0000f589 weight 999\n0000F589 walk_speed_max 0.75\n0000f589 preset zz_synth_fast\n0000f589 preset zz_synth_heavy\n",
        &p,
    );
    assert_eq!((report.accepted, report.preset_lines, report.replaced, report.rejected), (6, 2, 3, 1));
    assert_eq!(report.rejects(), &[(5, lo::Reject::OutOfRange)]);
    assert_eq!(table.len(), 1);
    // the rejected later value line does not disturb the value set before it
    assert_eq!((table.get(0xf589, 0), table.get(0xf589, 1), table.preset(0xf589)), (Some(70.0), Some(0.75), Some(1)));
}

#[test]
fn loadout_at_most_32_distinct_ids() {
    let p = synthetic();
    let mut body = String::new();
    for i in 1..=40u32 {
        if i % 2 == 0 {
            body += &format!("{:08x} weight {}\n", i, 60 + i);
        } else {
            body += &format!("{:08x} preset zz_synth_fast\n", i);
        }
    }
    // known ids still accept further keys and replacements after the table is full
    body += "00000005 walk_speed_max 1.25\n00000006 weight 61\n00000028 walk_speed_max 1.0\n00000029 preset zz_synth_fast\n";
    let (table, report) = lparse(2, &body, &p);
    assert_eq!((report.state, table.len()), (lo::FileState::Ok, 32));
    assert_eq!((report.accepted, report.replaced, report.rejected), (34, 1, 10));
    assert!(report.rejects().iter().all(|(_, why)| *why == lo::Reject::TooManyIds));
    assert_eq!(report.rejects()[0].0, 34); // line of the 33rd id
    assert_eq!(report.rejects().last().unwrap().0, 45);
    assert_eq!((table.get(32, 0), table.preset(31), table.preset(33), table.get(40, 1)), (Some(92.0), Some(0), None, None));
    assert_eq!((table.get(6, 0), table.get(5, 1), table.preset(5)), (Some(61.0), Some(1.25), Some(0)));
}

#[test]
fn loadout_reject_log_is_bounded_but_counts_everything() {
    let p = synthetic();
    let mut body = String::new();
    for _ in 0..200 {
        body += "zzz\n";
    }
    body += "0000f589 weight 130\n";
    let (table, report) = lparse(2, &body, &p);
    assert_eq!((report.rejected, report.rejects().len()), (200, 32));
    assert_eq!(report.rejects()[31], (33, lo::Reject::FieldCount));
    assert_eq!(table.get(0xf589, 0), Some(130.0));
    let all = [
        lo::Reject::NonUtf8, lo::Reject::FieldCount, lo::Reject::BadId, lo::Reject::ZeroId, lo::Reject::UnknownKey,
        lo::Reject::BadValue, lo::Reject::OutOfRange, lo::Reject::TooManyIds, lo::Reject::BadName, lo::Reject::UnknownPreset,
    ];
    let mut names: Vec<&str> = all.iter().map(|w| w.name()).collect();
    assert!(names.iter().all(|n| !n.is_empty() && n.bytes().all(|b| b.is_ascii_lowercase() || b == b'_' || b.is_ascii_digit())));
    names.sort();
    names.dedup();
    assert_eq!(names.len(), all.len());
}

fn check_table_invariants(table: &Table, p: &Presets) {
    assert!(table.len() <= lo::MAX_IDS);
    let mut ids: Vec<u32> = table.entries().iter().map(|e| e.id).collect();
    ids.sort();
    ids.dedup();
    assert_eq!(ids.len(), table.len(), "ids are unique");
    for entry in table.entries() {
        assert_ne!(entry.id, 0);
        assert!(entry.preset.is_some() || entry.has.iter().any(|h| *h), "no entry without content");
        if let Some(preset) = entry.preset {
            assert!(preset < p.len());
        }
        for key in 0..lo::KEYS {
            if entry.has[key] {
                assert!(lo::in_range(key, entry.value[key]));
            }
        }
    }
}

#[test]
fn loadout_arbitrary_bytes_never_panic_and_always_round_trip() {
    let p = synthetic();
    let mut next = rng(0x2545_f491_4f6c_dd1d);
    let alphabet = b"mc_loadouts 12\n\r\t #0123456789abcdefABCDEFweight walk_speed_max.-+\xff\xc3\xa9x";
    let words: [&[u8]; 8] = [
        b"\n0000f589 ", b"\n0000f58b ", b"preset ", b"zz_synth_fast\n", b"zz_synth_heavy\n", b"weight 1", b"walk_speed_max 1.", b"\n",
    ];
    let mut out = vec![0u8; lo::MAX_FILE];
    let mut with_content = 0;
    for round in 0..4000 {
        let len = (next() % 400) as usize;
        let mut bytes = match round % 3 {
            0 => b"mc_loadouts 1\n".to_vec(),
            1 => b"mc_loadouts 2\n".to_vec(),
            _ => Vec::new(),
        };
        for _ in 0..len {
            if next() % 8 != 0 {
                bytes.extend_from_slice(words[(next() % 8) as usize]);
            } else {
                bytes.push(alphabet[(next() % alphabet.len() as u64) as usize]);
            }
        }
        let (table, report) = lo::parse(&bytes, &p);
        check_table_invariants(&table, &p);
        if report.state != lo::FileState::Ok {
            assert_eq!(table.len(), 0);
        }
        if report.version == 1 {
            assert!(table.entries().iter().all(|e| e.preset.is_none()));
        }
        with_content += (table.len() != 0) as u32;
        // whatever was read serialises to a file that reads back as the same state
        let n = lo::serialise(&table, &p, &mut out).unwrap();
        let (back, again) = lo::parse(&out[..n], &p);
        assert_eq!((again.state, again.version, again.rejected), (lo::FileState::Ok, 2, 0));
        assert!(back == table, "round {round}");
    }
    assert!(with_content > 500, "the generator must reach real content: {with_content}");
}

// ---------------------------------------------------------------- serialisation

fn round_trip(table: &Table, p: &Presets) -> String {
    let mut out = vec![0u8; lo::MAX_FILE];
    let n = lo::serialise(table, p, &mut out).unwrap();
    let (back, report) = lo::parse(&out[..n], p);
    assert_eq!((report.state, report.version, report.rejected, report.replaced), (lo::FileState::Ok, 2, 0, 0));
    assert!(*back == *table);
    // and the text is a fixed point
    let mut again = vec![0u8; lo::MAX_FILE];
    let m = lo::serialise(&back, p, &mut again).unwrap();
    assert_eq!(&out[..n], &again[..m]);
    String::from_utf8(out[..n].to_vec()).unwrap()
}

#[test]
fn serialise_exact_text_and_stable_order() {
    let p = synthetic();
    assert_eq!(round_trip(&Table::new(), &p), "mc_loadouts 2\n");
    let mut t = Table::new();
    t.set(0xf58b, 1, 1.6).unwrap();
    t.set_preset(0xf589, 2).unwrap();
    t.set(0xf589, 1, 0.5).unwrap();
    t.set(0xf589, 0, 130.0).unwrap();
    t.set_preset(0xABCDEF01, 0).unwrap();
    assert_eq!(
        round_trip(&t, &p),
        "mc_loadouts 2\n0000f58b walk_speed_max 1.6\n0000f589 preset zz_synth_partial\n0000f589 weight 130\n0000f589 walk_speed_max 0.5\nabcdef01 preset zz_synth_fast\n"
    );
    // parse(serialise(x)) == x for a parsed file, and equality is not trivially true
    let (parsed, _) = lparse(2, "0000f589 preset zz_synth_fast\n0000f589 weight 61.25\n0000f58b walk_speed_max 1.155\n", &p);
    round_trip(&parsed, &p);
    let mut other = Table::new();
    other.set_preset(0xf589, 0).unwrap();
    other.set(0xf589, 0, 61.25).unwrap();
    other.set(0xf58b, 1, 1.155).unwrap();
    assert!(*parsed == other);
    other.set(0xf58b, 1, 1.1550001).unwrap();
    assert!(*parsed != other);
    other.set(0xf58b, 1, 1.155).unwrap();
    other.set_preset(0xf589, 1).unwrap();
    assert!(*parsed != other);
    other.set_preset(0xf589, 0).unwrap();
    assert!(*parsed == other);
    other.set(0xf58c, 0, 61.0).unwrap();
    assert!(*parsed != other);
    // order is part of the state
    let mut a = Table::new();
    a.set(1, 0, 61.0).unwrap();
    a.set(2, 0, 61.0).unwrap();
    let mut b = Table::new();
    b.set(2, 0, 61.0).unwrap();
    b.set(1, 0, 61.0).unwrap();
    assert!(a != b);
    assert_ne!(round_trip(&a, &p), round_trip(&b, &p));
}

#[test]
fn serialise_random_tables_round_trip() {
    let p = synthetic();
    let mut next = rng(7);
    for _ in 0..3000 {
        let mut t = Table::new();
        for _ in 0..(next() % 40) {
            let id = (next() % 48) as u32 + 1 + (((next() % 3) as u32) << 28);
            match next() % 4 {
                0 => {
                    let _ = t.set_preset(id, (next() % 3) as usize);
                }
                1 => {
                    // any f32 in the weight range, not only short decimals
                    let v = f32::from_bits(60.0f32.to_bits() + (next() % (140.0f32.to_bits() - 60.0f32.to_bits() + 1) as u64) as u32);
                    assert!(lo::in_range(0, v));
                    let _ = t.set(id, 0, v);
                }
                2 => {
                    let v = f32::from_bits(0.5f32.to_bits() + (next() % (2.0f32.to_bits() - 0.5f32.to_bits() + 1) as u64) as u32);
                    assert!(lo::in_range(1, v));
                    let _ = t.set(id, 1, v);
                }
                _ => {
                    t.clear_preset(id);
                }
            }
        }
        check_table_invariants(&t, &p);
        round_trip(&t, &p);
    }
}

#[test]
fn serialise_largest_table_fits_the_file_limit() {
    // 32 IDs, each with a 31-character preset name and both explicit keys at full length
    let mut body = String::new();
    for i in 0..32 {
        body += &format!("fighter {}{:02} 0x0000000001\n", "n".repeat(29), i);
    }
    let p = pload(&body).0;
    let mut t = Table::new();
    for i in 0..32u32 {
        t.set_preset(0xffff_ff00 + i, i as usize).unwrap();
        t.set(0xffff_ff00 + i, 0, 139.99998).unwrap();
        t.set(0xffff_ff00 + i, 1, 1.9999999).unwrap();
    }
    let text = round_trip(&t, &p);
    assert!(text.len() < lo::MAX_FILE / 2, "{}", text.len());
    assert_eq!(text.lines().count(), 1 + 3 * 32);
    // errors: buffer too small, preset index without a name
    let mut small = [0u8; 40];
    assert_eq!(lo::serialise(&t, &p, &mut small), Err(lo::SerError::Overflow));
    let mut exact = vec![0u8; text.len()];
    assert_eq!(lo::serialise(&t, &p, &mut exact), Ok(text.len()));
    let mut short = vec![0u8; text.len() - 1];
    assert_eq!(lo::serialise(&t, &p, &mut short), Err(lo::SerError::Overflow));
    let mut bad = Table::new();
    bad.set_preset(1, 99).unwrap();
    let mut out = vec![0u8; lo::MAX_FILE];
    assert_eq!(lo::serialise(&bad, &p, &mut out), Err(lo::SerError::Preset));
    let mut nan = Table::new();
    nan.set(1, 0, f32::NAN).unwrap();
    assert_eq!(lo::serialise(&nan, &p, &mut out), Err(lo::SerError::Number));
}

#[test]
fn format_value_is_shortest_and_exact() {
    let fmt = |v: f32| {
        let mut buf = [0u8; 24];
        lo::format_value(v, &mut buf).map(|n| String::from_utf8(buf[..n].to_vec()).unwrap())
    };
    for (v, want) in [
        (130.0f32, "130"), (1.6, "1.6"), (0.5, "0.5"), (60.0, "60"), (104.5, "104.5"), (1.155, "1.155"), (0.043, "0.043"),
        (0.0, "0"), (-1.5, "-1.5"), (1.0e-3, "0.001"), (16777216.0, "16777216"), (0.1, "0.1"), (139.99998, "139.99998"),
    ] {
        assert_eq!(fmt(v).as_deref(), Some(want), "{v}");
    }
    for v in [f32::NAN, f32::INFINITY, f32::NEG_INFINITY, f32::MAX, f32::MIN_POSITIVE, 1.0e-30, 1.0e30] {
        assert_eq!(fmt(v), None, "{v}");
    }
    let mut next = rng(42);
    let mut checked = 0;
    for _ in 0..1_000_000 {
        let v = f32::from_bits(next() as u32);
        if !v.is_finite() || v.abs() < 1.0e-4 || v.abs() >= 1.0e9 {
            continue;
        }
        let s = fmt(v).unwrap_or_else(|| panic!("no text for {v:e}"));
        assert_eq!(lo::parse_decimal(&s).map(f32::to_bits), Some(v.to_bits()), "{s}");
        // std's shortest round-trip text has the same number of significant digits
        let digits = |t: &str| t.trim_start_matches('-').replace('.', "").trim_start_matches('0').len();
        assert!(digits(&s) <= digits(&format!("{v}")) + 1, "{s} vs {v}");
        checked += 1;
    }
    assert!(checked > 100_000);
}

// ---------------------------------------------------------------- store and resolution order

fn store_of(body: &str, p: &Presets) -> Store {
    let (table, report) = lparse(2, body, p);
    assert_eq!(report.rejected, 0);
    let store = Store::new();
    store.publish(&table);
    store
}

#[test]
fn resolution_explicit_then_preset_then_game() {
    let p = synthetic();
    let f = |h: u64| p.fields.find(h).unwrap();
    let store = store_of(
        "0000f589 preset zz_synth_fast\n0000f589 weight 130\n0000f58b preset zz_synth_partial\n0000f58c walk_speed_max 1.6\n0000f58d preset zz_synth_heavy\n0000f58d weight 61\n0000f58d walk_speed_max 0.5\n",
        &p,
    );
    assert_eq!(store.len(), 4);
    let hit = |entry, value, src| Some(lo::Hit { entry, value, src });
    // f589: explicit weight wins over the preset's 70; everything else from the preset
    assert_eq!(store.resolve(0xf589, f(W), &p), hit(0, 130.0, Src::Explicit));
    assert_eq!(store.resolve(0xf589, f(WS), &p), hit(0, 1.5, Src::Preset));
    assert_eq!(store.resolve(0xf589, f(TEN[2]), &p), hit(0, 2.5, Src::Preset));
    assert_eq!(store.resolve(0xf589, f(TEN[9]), &p), hit(0, 0.75, Src::Preset));
    // f58b: a preset with three fields; the other seven are the game's
    assert_eq!(store.resolve(0xf58b, f(W), &p), hit(1, 999.5, Src::Preset)); // preset values are not range-limited
    assert_eq!(store.resolve(0xf58b, f(WS), &p), None);
    assert_eq!(store.resolve(0xf58b, f(TEN[2]), &p), None);
    assert_eq!(store.resolve(0xf58b, f(TEN[8]), &p), hit(1, 12.5, Src::Preset));
    // f58c: explicit only
    assert_eq!(store.resolve(0xf58c, f(WS), &p), hit(2, 1.6, Src::Explicit));
    assert_eq!(store.resolve(0xf58c, f(W), &p), None);
    assert_eq!(store.resolve(0xf58c, f(TEN[5]), &p), None);
    // f58d: both explicit keys over a full preset
    assert_eq!(store.resolve(0xf58d, f(W), &p), hit(3, 61.0, Src::Explicit));
    assert_eq!(store.resolve(0xf58d, f(WS), &p), hit(3, 0.5, Src::Explicit));
    assert_eq!(store.resolve(0xf58d, f(TEN[4]), &p), hit(3, 0.8, Src::Preset));
    // unknown ID, ID 0, field indexes that do not exist
    for field in 0..12 {
        assert_eq!(store.resolve(0xf58e, field, &p), None);
        assert_eq!(store.resolve(0, field, &p), None);
    }
    for field in [10, 11, 49, 50, 63, 64, usize::MAX] {
        assert_eq!(store.resolve(0xf589, field, &p), None, "{field}");
    }
    assert_eq!((store.preset_of(0), store.preset_of(1), store.preset_of(2), store.preset_of(3), store.preset_of(4)), (Some(0), Some(2), None, Some(1), None));
    // an explicit key index is never taken for another field: field 2 has no explicit value
    assert_eq!(store.resolve(0xf58c, 2, &p), None);
}

#[test]
fn store_publish_snapshot_and_first_apply() {
    let p = synthetic();
    let store = Store::new();
    assert_eq!((store.len(), store.resolve(0xf589, 0, &p)), (0, None));
    assert!(*store.snapshot() == Table::new());
    let (table, _) = lparse(2, "0000f589 preset zz_synth_fast\n0000f589 weight 130\n0000f58c walk_speed_max 1.6\n0000f58b preset zz_synth_heavy\n", &p);
    store.publish(&table);
    assert_eq!(store.len(), 3);
    assert!(store.snapshot() == table);
    // once per (entry, field index), for every field index the table can hold
    for entry in 0..3 {
        for field in 0..pr::FIELDS {
            assert!(store.first_apply(entry, field), "{entry} {field}");
            assert!(!store.first_apply(entry, field));
        }
    }
    assert!(!store.first_apply(99, 0) && !store.first_apply(0, 64) && !store.first_apply(0, usize::MAX));
    // a full table
    let mut body = String::new();
    for i in 1..=32u32 {
        body += &format!("{:08x} preset zz_synth_heavy\n{:08x} walk_speed_max 1.5\n", i << 8, i << 8);
    }
    let (table, _) = lparse(2, &body, &p);
    store.publish(&table);
    assert_eq!(store.len(), 32);
    assert!(store.snapshot() == table);
    assert_eq!(store.resolve(32 << 8, 1, &p).map(|h| (h.entry, h.value, h.src)), Some((31, 1.5, Src::Explicit)));
    assert_eq!(store.resolve(32 << 8, 0, &p).map(|h| (h.value, h.src)), Some((135.0, Src::Preset)));
    assert_eq!(store.resolve(0xf589, 0, &p), None);
    assert!(store.first_apply(0, 0), "publish resets the applied marks");
    // an empty table switches everything off again
    store.publish(&Table::new());
    assert_eq!((store.len(), store.resolve(1 << 8, 1, &p), store.preset_of(0)), (0, None, None));
    // ID 0 never has a loadout, even if a table made in memory (not by the parser) holds one
    let mut zero = Table::new();
    zero.set_preset(0, 0).unwrap();
    zero.set(0, 0, 130.0).unwrap();
    zero.set(7, 0, 61.0).unwrap();
    store.publish(&zero);
    assert_eq!(store.len(), 2);
    for field in 0..10 {
        assert_eq!(store.resolve(0, field, &p), None);
    }
    assert_eq!(store.resolve(7, 0, &p).map(|h| h.value), Some(61.0));
}

// ---------------------------------------------------------------- decision

fn facts() -> Facts {
    Facts { fighter_cat: 0, cat_accessor: 0, round_trip: true, cat_object: 0, kind_accessor: GUNNER, kind_object: GUNNER, entry_accessor: 1, entry_object: 1 }
}

#[test]
fn constants_match_the_reports() {
    assert_eq!(pr::HASH_WEIGHT, 0x0607cd5541);
    assert_eq!(pr::HASH_WALK_SPEED_MAX, 0x0ee2ec2860);
    assert_eq!(KIND_MIIGUNNER, 74);
    assert_eq!(ACCEPTED_KINDS, [74]);
    assert_eq!(TABLE_BASE, 0x5307760);
    assert_eq!(VTABLE_WORK, 0x4f89490);
    assert_eq!(VTABLE_OTHER, 0x4f73738);
    assert_eq!(PARENT_WORK_OFFSET, 0x50);
    assert_eq!(id_addr(0, 0), Some(0x53085b8));
    assert_eq!(special_addr(0, 0), Some(0x5307802));
    assert_eq!(id_addr(0, 1), Some(0x53085b8 + 0x240));
    assert_eq!(id_addr(0x7100000000, 7), Some(0x7100000000 + 0x5307760 + 0xe58 + 7 * 0x240));
    assert_eq!((id_addr(0, 8), special_addr(0, 8), id_addr(0, u32::MAX)), (None, None, None));
    assert_eq!((SITE_PARAM.offset, SITE_PARAM.words), (0x4e53e0, [0xf9401c00, 0xf9400008, 0xf9401903, 0xd61f0060]));
    assert_eq!(core::mem::size_of::<Site>(), 24);
    assert!(words_equal(&SITE_PARAM.words, &SITE_PARAM.words));
    assert!(!words_equal(&SITE_PARAM.words, &[0xf9401c00, 0xf9400008, 0xf9401d03, 0xd61f0060]));
    assert_eq!((L3_HASHES_PER_PARENT, SEEN_SLOTS, L5_FIRST), (16, 64, 600));
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
    let p = synthetic();
    let f = |h: u64| p.fields.find(h).unwrap();
    let store = store_of("0000f589 preset zz_synth_fast\n0000f589 weight 130\n0000aaaa weight 70\n", &p);
    let kinds = &ACCEPTED_KINDS;
    let gunner = Ident { st: St::Ok, kind: GUNNER, player: 0 };
    let ok = |entry, value, src| Decision { st: St::Ok, entry, value: Some(value), src: Some(src) };
    assert_eq!(decide(&gunner, kinds, 0xf589, &store, &p, f(W)), ok(0, 130.0, Src::Explicit));
    assert_eq!(decide(&gunner, kinds, 0xf589, &store, &p, f(WS)), ok(0, 1.5, Src::Preset));
    assert_eq!(decide(&gunner, kinds, 0xf589, &store, &p, f(TEN[6])), ok(0, 0.2, Src::Preset));
    // same saved fighter on another port
    let port2 = Ident { player: 1, ..gunner };
    assert_eq!(decide(&port2, kinds, 0xf589, &store, &p, f(TEN[8])).value, Some(40.0));
    // the other Gunner: no entry, for every field
    for field in 0..10 {
        assert_eq!(decide(&port2, kinds, 0xf58b, &store, &p, field), Decision::vanilla(St::NoEntry));
    }
    // an entry without preset: its explicit key only
    assert_eq!(decide(&gunner, kinds, 0xaaaa, &store, &p, f(W)), ok(1, 70.0, Src::Explicit));
    assert_eq!(decide(&gunner, kinds, 0xaaaa, &store, &p, f(WS)), Decision::vanilla(St::NoEntry));
    assert_eq!(decide(&gunner, kinds, 0xaaaa, &store, &p, f(TEN[3])), Decision::vanilla(St::NoEntry));
    // slot id 0 (default Mii, or nothing in the slot)
    assert_eq!(decide(&gunner, kinds, 0, &store, &p, f(W)), Decision::vanilla(St::NoSlotId));
    // not an accepted kind, even if the slot still holds a known id
    for kind in [0, 0x48, 0x49, 0x4b, -1] {
        for field in [f(W), f(TEN[4])] {
            assert_eq!(decide(&Ident { kind, ..gunner }, kinds, 0xf589, &store, &p, field), Decision::vanilla(St::NotGunner));
        }
    }
    // the kinds are one list: a second kind is accepted by adding it, an empty list accepts nobody
    assert_eq!(decide(&Ident { kind: 0x48, ..gunner }, &[GUNNER, 0x48], 0xf589, &store, &p, f(W)).value, Some(130.0));
    assert_eq!(decide(&gunner, &[0x48], 0xf589, &store, &p, f(W)), Decision::vanilla(St::NotGunner));
    assert_eq!(decide(&gunner, &[], 0xf589, &store, &p, f(W)), Decision::vanilla(St::NotGunner));
    // identity not resolved: the reason is passed through, never an override
    for st in [St::Off, St::Vtable, St::NoParent, St::BackPtr, St::Reentry, St::GuardFull, St::Category, St::RoundTrip, St::Category2, St::KindMismatch, St::EntryMismatch, St::EntryRange] {
        let d = decide(&Ident { st, kind: GUNNER, player: 0 }, kinds, 0xf589, &store, &p, f(W));
        assert_eq!(d, Decision::vanilla(st));
    }
    for player in [-1, 8, 100] {
        assert_eq!(decide(&Ident { player, ..gunner }, kinds, 0xf589, &store, &p, f(W)), Decision::vanilla(St::EntryRange));
    }
    // empty store; field index that does not exist
    assert_eq!(decide(&gunner, kinds, 0xf589, &Store::new(), &p, f(W)), Decision::vanilla(St::NoEntry));
    assert_eq!(decide(&gunner, kinds, 0xf589, &store, &p, 10), Decision::vanilla(St::NoEntry));
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
    assert_eq!((Src::Explicit as usize, Src::Preset as usize, lo::SRC_COUNT), (0, 1, 2));
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
fn seen_table_logs_the_first_request_per_fighter_and_field() {
    let t = SeenTable::new();
    let gunner = Ident { st: St::Ok, kind: GUNNER, player: 0 };
    let a = seen_key(0xaaa0, &gunner, 0xf589);
    assert_eq!(t.observe(a, 0), Seen { slot: Some(0), is_new: true, log: true });
    // the same field again: never logged again
    for _ in 0..50 {
        assert_eq!(t.observe(a, 0), Seen { slot: Some(0), is_new: false, log: false });
    }
    // other fields: once each, ten fields fit
    for field in 1..10 {
        assert_eq!(t.observe(a, field), Seen { slot: Some(0), is_new: false, log: true });
        assert!(!t.observe(a, field).log);
    }
    // at most 16 field hashes per fighter
    let logged: usize = (10..40).filter(|field| t.observe(a, *field).log).count();
    assert_eq!(logged, 6);
    assert!(!t.observe(a, 40).log && !t.observe(a, 5).log);
    // field indexes that do not fit the mask are counted as overflow, not logged
    assert_eq!(t.observe(a, 64), Seen { slot: None, is_new: false, log: false });
    assert_eq!((t.distinct(), t.overflow()), (1, 1));

    // the same parent address with another identity is another fighter: its lines are new
    for (i, key) in [
        seen_key(0xaaa0, &gunner, 0xf58b),                          // another saved Mii at the same address
        seen_key(0xaaa0, &Ident { player: 1, ..gunner }, 0xf589),   // same Mii on another port
        seen_key(0xaaa0, &Ident { kind: 0, ..gunner }, 0xf589),     // another character at the same address
        seen_key(0xaaa0, &Ident::unknown(St::RoundTrip), 0),        // identity not resolved yet
        seen_key(0xbbb0, &gunner, 0xf589),                          // another parent
        seen_key(0, &Ident::unknown(St::Vtable), 0),                // not a fighter work object
    ]
    .iter()
    .enumerate()
    {
        assert_eq!(t.observe(*key, 0), Seen { slot: Some(i + 1), is_new: true, log: true }, "{i}");
        assert_eq!(t.observe(*key, 0), Seen { slot: Some(i + 1), is_new: false, log: false });
        assert_ne!(*key, 0);
    }
    assert_eq!(t.observe(0, 3).slot, Some(7)); // key 0 is stored as a key of its own
    assert_eq!(t.distinct(), 8);
    // the outcome is not part of the identity: `st` of a resolved fighter does not make a new key
    assert_eq!(seen_key(0xaaa0, &gunner, 0xf589), a);

    let full = SeenTable::new();
    for parent in 1..=70u64 {
        full.observe(seen_key(parent << 8, &gunner, 0xf589), 0);
    }
    assert_eq!((full.distinct(), full.overflow()), (64, 6));
}

#[test]
fn field_flags_and_totals_schedule() {
    let flags = FieldFlags::new();
    for field in 0..64 {
        assert!(flags.first(field));
        assert!(!flags.first(field));
    }
    assert!(!flags.first(64) && !flags.first(usize::MAX));
    assert_eq!(flags.get(), u64::MAX);
    let due: Vec<u32> = (0..40_000).filter(|n| totals_due(*n)).collect();
    assert_eq!(due, [600, 1200, 2400, 4800, 9600, 19200, 38400]);
    assert!(totals_due(600 << 20) && !totals_due(u32::MAX) && !totals_due(0) && !totals_due(1800));
    let counter = std::sync::atomic::AtomicU32::new(0);
    assert_eq!((count_event(&counter, 2), count_event(&counter, 2), count_event(&counter, 2)), ((1, true), (2, true), (3, false)));
}

#[test]
fn formatting() {
    let mut b: LineBuf<200> = LineBuf::new();
    b.s("mc|L3").s("|h=").hash40(W).s("|p=").int(-1).s("|kind=").int(74).s("|id=").hex_fixed(0xf589, 8).s("|orig=").f32_dec(104.0).s("|v=").f32_dec(1.6);
    b.s("|x=").hex(0x24730e8d80).s("|n=").dec(0).s("|m=").int(i64::MIN).s("|preset=").bytes(b"zz_synth_fast").end_line();
    assert_eq!(text(&b), "mc|L3|h=0x0607cd5541|p=-1|kind=74|id=0000f589|orig=104.0000|v=1.6000|x=0x24730e8d80|n=0|m=-9223372036854775808|preset=zz_synth_fast\n");
    let mut small: LineBuf<8> = LineBuf::new();
    small.s("0123456789abcdef").end_line();
    assert_eq!(small.as_bytes(), b"0123456\n");
    let mut p: LineBuf<64> = LineBuf::new();
    push_player(&mut p, 1, 0xf58b, [2, 2, 2, 2]);
    assert_eq!(text(&p), "|p1=0000f58b:02020202");
    let mut h: LineBuf<32> = LineBuf::new();
    h.hash40(0x111).s(" ").f32_dec(0.087).s(" ").f32_dec(0.043);
    assert_eq!(text(&h), "0x0000000111 0.0870 0.0430");
}
