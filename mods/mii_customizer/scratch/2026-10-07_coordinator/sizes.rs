//! Coordinator (session 4 boot crash): sizes of the plugin's big value types on the host.
//! The plugin's load code runs on a 64 KiB Skyline thread stack.
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

use std::mem::size_of;

fn main() {
    println!("menu::Menu        {}", size_of::<menu::Menu>());
    println!("menu::Entry       {}", size_of::<menu::Entry>());
    println!("menu::Report      {}", size_of::<menu::Report>());
    println!("loadout::Table    {}", size_of::<loadout::Table>());
    println!("loadout::Entry    {}", size_of::<loadout::Entry>());
    println!("loadout::Store    {}", size_of::<loadout::Store>());
    println!("loadout::Report   {}", size_of::<loadout::Report>());
    println!("names::Names      {}", size_of::<names::Names>());
    println!("list::List        {}", size_of::<list::List>());
    println!("preset::Presets   {}", size_of::<preset::Presets>());
}
