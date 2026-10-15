#![allow(dead_code)]
#[path = "../../plugin/src/list.rs"] mod list;
#[path = "../../plugin/src/loadout.rs"] mod loadout;
#[path = "../../plugin/src/logic.rs"] mod logic;
#[path = "../../plugin/src/menu.rs"] mod menu;
#[path = "../../plugin/src/names.rs"] mod names;
#[path = "../../plugin/src/preset.rs"] mod preset;
#[path = "../../plugin/src/ui.rs"] mod ui;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 4 { std::process::exit(2); }
    let presets = Box::new(preset::Presets::new());
    presets.init_named();
    let p = preset::parse(&std::fs::read(&args[1]).unwrap(), &presets);
    let (l, lr) = list::parse(Some(&std::fs::read(&args[2]).unwrap()), &presets);
    let (n, nr) = names::parse(Some(&std::fs::read(&args[3]).unwrap()), &presets);
    println!("presets={} rejected={}", p.presets, p.rejected);
    println!("list state={:?} fallback={} accepted={} rejected={} count={}",
        lr.state, lr.fallback, lr.accepted, lr.rejected, l.len());
    println!("names state={:?} accepted={} rejected={} default={}",
        nr.state, nr.accepted, nr.rejected,
        String::from_utf8_lossy(n.default_name()));
    let ok = p.state == preset::FileState::Ok && p.presets == 94 && p.rejected == 0
        && lr.state == list::FileState::Ok && !lr.fallback && lr.accepted == 85
        && lr.rejected == 0 && l.len() == 85
        && nr.state == names::FileState::Ok && nr.accepted == 86
        && nr.rejected == 0 && n.default_name() == b"Mii Gunner";
    std::process::exit(if ok { 0 } else { 1 });
}
