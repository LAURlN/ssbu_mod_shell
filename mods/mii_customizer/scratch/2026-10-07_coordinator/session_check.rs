//! Coordinator: parse the session-3 card files with the plugin's own parsers (sources
//! compiled unchanged) and print what the plugin would see. Arguments: presets, list, menu.
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

use menu::Page;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let presets = Box::new(preset::Presets::new());
    presets.init_named();
    let pr = preset::parse(&std::fs::read(&args[1]).unwrap(), &presets);
    println!("presets state_ok={} presets={} rejected={}", pr.state == preset::FileState::Ok, pr.presets, pr.rejected);
    let (l, lr) = list::parse(Some(&std::fs::read(&args[2]).unwrap()), &presets);
    println!("list state_ok={} fallback={} accepted={} rejected={} len={}",
        lr.state == list::FileState::Ok, lr.fallback, lr.accepted, lr.rejected, l.len());
    let (m, mr) = menu::parse(Some(&std::fs::read(&args[3]).unwrap()), &presets);
    println!("menu state_ok={} entries={} labels={} allows={} rejected={} len={}",
        mr.state == menu::FileState::Ok, mr.entries, mr.labels, mr.allows, mr.rejected, m.len());
    println!("first_page_main={}", menu::first_page(&m) == Page::Main);
    println!("rows main={} entry0={} entry1={}", menu::rows(Page::Main, &m, &l),
        menu::rows(Page::Entry(0), &m, &l), menu::rows(Page::Entry(1), &m, &l));
    for (name, page) in [("main", Page::Main), ("entry0", Page::Entry(0)), ("entry1", Page::Entry(1))] {
        let mask = menu::available_mask(page, &m, &l);
        let n: u32 = mask.iter().map(|w| w.count_ones()).sum();
        println!("available {}={} row0_label={}", name, n,
            String::from_utf8_lossy(menu::row_label(page, 0, &m, &l)));
    }
    let mut i = 0;
    while let Some(e) = m.entry(i) {
        let t = e.text_c();
        let end = t.iter().position(|&b| b == 0).unwrap();
        println!("{:2} {:16} label={:32} text={}", i, String::from_utf8_lossy(e.id()),
            String::from_utf8_lossy(e.label()), String::from_utf8_lossy(&t[..end]));
        i += 1;
    }
    let ok = pr.rejected == 0 && lr.rejected == 0 && !lr.fallback && l.len() == 86
        && mr.rejected == 0 && m.len() == 24;
    println!("{}", if ok { "SESSION FILES OK" } else { "SESSION FILES NOT OK" });
    std::process::exit(if ok { 0 } else { 1 });
}
