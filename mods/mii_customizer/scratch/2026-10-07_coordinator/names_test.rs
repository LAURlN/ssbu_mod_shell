//! Coordinator host tests for plugin/src/names.rs (0.5.2). Sources compiled unchanged.
//! Run: rustc --test, with NAMES_FILE / PRESETS_FILE pointing at the session files.
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

use names::{compose, FileState, LINE_BUF};

fn presets() -> Box<preset::Presets> {
    let p = Box::new(preset::Presets::new());
    p.init_named();
    let r = preset::parse(&std::fs::read(env!("PRESETS_FILE")).unwrap(), &p);
    assert_eq!((r.presets, r.rejected), (94, 0));
    p
}

fn parse(body: &str, p: &preset::Presets) -> (Box<names::Names>, names::Report) {
    let (n, r) = names::parse(Some(body.as_bytes()), p);
    (Box::new(n), r)
}

fn s(out: &[u8; LINE_BUF]) -> &str {
    let end = out.iter().position(|b| *b == 0).unwrap();
    std::str::from_utf8(&out[..end]).unwrap()
}

#[test]
fn session_file() {
    let p = presets();
    let (n, r) = names::parse(Some(&std::fs::read(env!("NAMES_FILE")).unwrap()), &p);
    assert_eq!((r.state, r.accepted, r.rejected), (FileState::Ok, 87, 0));
    assert_eq!(n.name(p.find_name(b"kirby").unwrap()), b"Kirby");
    assert_eq!(n.default_name(), b"Mii Gunner");
    assert_eq!(n.value(None), b"Mii Gunner");
    assert_eq!(n.value(p.find_name(b"dedede")), b"King Dedede");
}

#[test]
fn file_states() {
    let p = presets();
    let (n, r) = names::parse(None, &p);
    assert_eq!(r.state, FileState::Absent);
    assert!(n.default_name().is_empty() && n.value(Some(3)).is_empty());
    assert_eq!(parse("mc_names 2\nkirby K\n", &p).1.state, FileState::BadVersionLine);
    assert_eq!(parse("\u{feff}mc_names 1\nkirby K\n", &p).1.state, FileState::BadVersionLine);
    assert_eq!(parse(" mc_names 1\nkirby K\n", &p).1.state, FileState::BadVersionLine);
    let big = vec![b'#'; names::MAX_FILE + 1];
    assert_eq!(names::parse(Some(&big), &p).1.state, FileState::TooLarge);
    let (n, r) = parse("mc_names 2\nkirby K\n", &p);
    assert!(n.name(p.find_name(b"kirby").unwrap()).is_empty() && r.accepted == 0);
}

#[test]
fn lines() {
    let p = presets();
    let long = "x".repeat(41);
    let body = format!(
        "mc_names 1\r\n# c\r\n\r\nkirby   Kirby #1  \r\nkirby Again\nnosuch X\nKIRBY X\nfox\nmario {long}\nlink \u{1F600}\nsamus Sam\tus\ndonkey D\u{e9}\n");
    let (n, r) = parse(&body, &p);
    assert_eq!(r.state, FileState::Ok);
    assert_eq!(n.name(p.find_name(b"kirby").unwrap()), b"Kirby #1");
    assert_eq!(n.name(p.find_name(b"donkey").unwrap()), "D\u{e9}".as_bytes());
    assert!(n.name(p.find_name(b"fox").unwrap()).is_empty());
    assert!(n.name(p.find_name(b"mario").unwrap()).is_empty());
    assert!(n.name(p.find_name(b"link").unwrap()).is_empty());
    assert!(n.name(p.find_name(b"samus").unwrap()).is_empty());
    assert_eq!((r.accepted, r.rejected, r.first_reject), (2, 7, 5));
    assert!(n.default_name().is_empty()); // no miigunner line
    assert!(n.name(9999).is_empty());
}

#[test]
fn composing() {
    let mut out = [0xffu8; LINE_BUF];
    assert_eq!(compose(&mut out, b"Stats", b"Kirby"), 12);
    assert_eq!(s(&out), "Stats: Kirby");
    compose(&mut out, b"Jab", b"");
    assert_eq!(s(&out), "Jab");
    let t = [b'a'; 40];
    let v = [b'b'; 40];
    assert_eq!(compose(&mut out, &t, &v), 82);
    assert_eq!(out[82], 0);
    let t = [b'a'; 200];
    assert_eq!(compose(&mut out, &t, &t), 82);
    assert_eq!(out[LINE_BUF - 1], 0);
    compose(&mut out, b"", b"");
    assert_eq!(s(&out), "");
}
