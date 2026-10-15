//! Motion-list patch files for ARCropolis (`motion_list.motdiff`), with the same library and
//! YAML shape as the `yamlist` tool (motion_lib `Diff`).
//!
//!   motdiff diff  <a.bin> <b.bin> <out.motdiff>   patch that turns list a into list b
//!   motdiff patch <base.bin> <in.motdiff> <out.bin>   apply a patch the way ARCropolis does
use motion_lib::diff::Diff;
use motion_lib::mlist::{MList, MListDiff};
use std::process::ExitCode;

fn run(args: &[String]) -> Result<(), String> {
    let e = |x: &dyn std::fmt::Debug| format!("{x:?}");
    match args {
        [mode, a, b, out] if mode == "diff" => {
            let a = motion_lib::open(a).map_err(|x| e(&x))?;
            let b = motion_lib::open(b).map_err(|x| e(&x))?;
            let diff = a.diff(&b);
            std::fs::write(out, serde_yaml::to_string(&diff).map_err(|x| e(&x))?).map_err(|x| e(&x))
        }
        [mode, base, patch, out] if mode == "patch" => {
            let mut list: MList = motion_lib::open(base).map_err(|x| e(&x))?;
            let text = std::fs::read_to_string(patch).map_err(|x| e(&x))?;
            let diff: MListDiff = serde_yaml::from_str(&text).map_err(|x| e(&x))?;
            list.apply(&diff);
            motion_lib::save(out, &list).map_err(|x| e(&x))
        }
        _ => Err("usage: motdiff diff <a.bin> <b.bin> <out.motdiff> | motdiff patch <base.bin> <in.motdiff> <out.bin>".into()),
    }
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match run(&args) {
        Ok(()) => ExitCode::SUCCESS,
        Err(why) => {
            eprintln!("motdiff: {why}");
            ExitCode::FAILURE
        }
    }
}
