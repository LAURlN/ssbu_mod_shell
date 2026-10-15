//! Run the plugin's preset parser (plugin/src/preset.rs, unchanged) over a file on the host.
//! usage: preset_report <presets.txt> [--dump]
//! Prints the load result the plugin would log; with --dump also one line per stored value
//! (`<preset> <kind hash> <field hash> <f32 bits>`), for comparison with an independent reader.
#![allow(dead_code)]

#[path = "../../plugin/src/loadout.rs"]
mod loadout;
#[path = "../../plugin/src/preset.rs"]
mod preset;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let bytes = std::fs::read(&args[1]).expect("read");
    let p = Box::new(preset::Presets::new());
    p.init_named();
    let r = preset::parse(&bytes, &p);
    println!(
        "state={} bytes={} lines={} presets={} hashes={} field_lines={} rejected={} skipped={}",
        r.state.name(), bytes.len(), r.lines, p.len(), p.file_hashes(), r.fields, r.rejected, r.skipped
    );
    println!("fields n={} probe_max={}", p.fields.len(), p.fields.probe_max());
    for field in 0..p.fields.len() {
        let hash = p.fields.hash_of(field);
        println!("field {field} 0x{hash:010x} home_slot={}", preset::home_slot(hash));
    }
    for (line, why) in r.rejects() {
        println!("reject line={line} reason={}", why.name());
    }
    let (mut min_fields, mut max_fields, mut longest) = (u32::MAX, 0, 0);
    for i in 0..p.len() {
        let mut buf = [0u8; preset::NAME_BUF];
        let len = p.name(i, &mut buf);
        min_fields = min_fields.min(p.field_count(i));
        max_fields = max_fields.max(p.field_count(i));
        longest = longest.max(len);
        if args.iter().any(|a| a == "--dump") {
            let name = std::str::from_utf8(&buf[..len]).unwrap();
            for field in 0..p.fields.len() {
                if let Some(v) = p.value(i, field) {
                    println!("value {name} 0x{:010x} 0x{:010x} {:08x}", p.kind(i), p.fields.hash_of(field), v.to_bits());
                }
            }
        }
    }
    println!("fields_per_preset min={min_fields} max={max_fields} longest_name={longest}");
}
