//! pmclone_trace: experimental state recorder and input replay for Training mode.
//!
//! Purpose: prove that a clone fighter behaves *identically* to the vanilla one.
//! The same recorded inputs are replayed on both, every fighter/article state is
//! written per frame, and `tools/trace_diff.py` compares the two files.
//! See trace/README.md for usage, file formats and known gaps.
#![feature(proc_macro_hygiene)]
#![allow(non_snake_case, non_upper_case_globals, static_mut_refs, unused_unsafe)]

mod input;
mod names;
mod sample;
mod session;
mod work_ids;

pub const VERSION: &str = env!("CARGO_PKG_VERSION");

#[skyline::main(name = "pmclone_trace")]
pub fn main() {
    session::boot_log(&format!("pmclone_trace v{} loaded", VERSION));
    session::prepare_dirs();
    input::install();
    sample::install();
}
