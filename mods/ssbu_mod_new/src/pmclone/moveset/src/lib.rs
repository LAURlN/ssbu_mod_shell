#![feature(proc_macro_hygiene)]
#![allow(non_snake_case, non_upper_case_globals, unused_imports, unused_variables)]

pub use smashline::skyline_smash as smash;

pub mod names;
pub mod acmd;

#[skyline::main(name = "pmclone_moveset")]
pub fn main() {
    #[cfg(feature = "acmd_port")]
    acmd::install();
}
