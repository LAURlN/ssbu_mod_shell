//! Extract individual files from a Smash Ultimate `data.arc` by their ARC path.
//!
//! arc-extract --arc <data.arc> --out <dir> [--region us_en] [--index <paths.txt>] [--list] <path>...
//!
//! A `<path>` is an exact ARC path (`fighter/brave/param/vl.prc`). With `--index` (a text file with
//! one ARC path per line, first tab-separated column) a path may also be a folder (`fighter/brave/param/`)
//! or contain `*` wildcards; it then expands to every matching line of the index.
//! Files are written to `<out>/<arc path>`; nothing else is touched and the archive is opened read-only.

use sha2::{Digest, Sha256};
use smash_arc::{ArcFile, ArcLookup, Hash40, Region};
use std::path::{Path, PathBuf};
use std::process::ExitCode;
use std::str::FromStr;

const USAGE: &str = "usage: arc-extract --arc <data.arc> --out <dir> [--region us_en] \
[--index <paths.txt>] [--list] <arc path | folder/ | pattern*> ...";

struct Args {
    arc: PathBuf,
    out: PathBuf,
    region: String,
    index: Option<PathBuf>,
    list: bool,
    paths: Vec<String>,
}

fn parse_args() -> Result<Args, String> {
    let (mut arc, mut out, mut index) = (None, None, None);
    let (mut region, mut list, mut paths) = ("us_en".to_string(), false, Vec::new());
    let mut it = std::env::args().skip(1);
    while let Some(arg) = it.next() {
        let mut value = |name: &str| it.next().ok_or(format!("{name} needs a value"));
        match arg.as_str() {
            "--arc" => arc = Some(PathBuf::from(value("--arc")?)),
            "--out" => out = Some(PathBuf::from(value("--out")?)),
            "--index" => index = Some(PathBuf::from(value("--index")?)),
            "--region" => region = value("--region")?,
            "--list" => list = true,
            "-h" | "--help" => return Err(USAGE.into()),
            other if other.starts_with("--") => return Err(format!("unknown option {other}")),
            _ => paths.push(arg.replace('\\', "/")),
        }
    }
    if paths.is_empty() {
        return Err(USAGE.into());
    }
    Ok(Args {
        arc: arc.ok_or("--arc is required")?,
        out: out.ok_or("--out is required")?,
        region,
        index,
        list,
        paths,
    })
}

/// `*` matches any run of characters, including `/`.
fn glob(pattern: &str, text: &str) -> bool {
    let parts: Vec<&str> = pattern.split('*').collect();
    if parts.len() == 1 {
        return pattern == text;
    }
    let (first, last) = (parts[0], parts[parts.len() - 1]);
    if !text.starts_with(first) || text.len() < first.len() + last.len() || !text.ends_with(last) {
        return false;
    }
    let mut rest = &text[first.len()..text.len() - last.len()];
    for part in &parts[1..parts.len() - 1] {
        match rest.find(part) {
            Some(at) => rest = &rest[at + part.len()..],
            None => return false,
        }
    }
    true
}

fn expand(paths: &[String], index: Option<&Path>) -> Result<Vec<String>, String> {
    let needs_index = |p: &String| p.ends_with('/') || p.contains('*');
    let mut lines = Vec::new();
    if paths.iter().any(needs_index) {
        let index = index.ok_or("folders and * patterns need --index <file with one ARC path per line>")?;
        let text = std::fs::read_to_string(index).map_err(|e| format!("{}: {e}", index.display()))?;
        lines = text
            .lines()
            .map(|l| l.split('\t').next().unwrap_or("").trim().to_string())
            .filter(|l| !l.is_empty())
            .collect();
    }
    let mut result = Vec::new();
    for path in paths {
        if !needs_index(path) {
            result.push(path.clone());
            continue;
        }
        let pattern = if path.ends_with('/') { format!("{path}*") } else { path.clone() };
        let before = result.len();
        result.extend(lines.iter().filter(|l| glob(&pattern, l)).cloned());
        if result.len() == before {
            return Err(format!("{path}: no line of the index matches"));
        }
    }
    result.sort();
    result.dedup();
    Ok(result)
}

fn main() -> ExitCode {
    let args = match parse_args() {
        Ok(args) => args,
        Err(message) => {
            eprintln!("{message}");
            return ExitCode::from(2);
        }
    };
    let paths = match expand(&args.paths, args.index.as_deref()) {
        Ok(paths) => paths,
        Err(message) => {
            eprintln!("{message}");
            return ExitCode::from(2);
        }
    };
    if args.list {
        paths.iter().for_each(|p| println!("{p}"));
        return ExitCode::SUCCESS;
    }
    let region = Region::from_str(&args.region).unwrap();
    if region == Region::None && args.region != "none" {
        eprintln!("unknown region {} (use e.g. us_en, eu_de, jp_ja)", args.region);
        return ExitCode::from(2);
    }
    let arc = match ArcFile::open(&args.arc) {
        Ok(arc) => arc,
        Err(e) => {
            eprintln!("cannot open {}: {e}", args.arc.display());
            return ExitCode::from(1);
        }
    };
    let mut failed = 0;
    for path in &paths {
        let contents = match arc.get_file_contents(Hash40::from(path.as_str()), region) {
            Ok(contents) => contents,
            Err(e) => {
                eprintln!("MISSING\t{path}\t{e}");
                failed += 1;
                continue;
            }
        };
        // `stream:/...` and `prebuilt:/...` are not legal Windows paths; ArcExplorer writes them with `;`.
        let target = args.out.join(path.replace("stream:/", "stream;/").replace("prebuilt:/", "prebuilt;/"));
        let written = target
            .parent()
            .map_or(Ok(()), std::fs::create_dir_all)
            .and_then(|_| std::fs::write(&target, &contents));
        if let Err(e) = written {
            eprintln!("WRITE-FAILED\t{path}\t{e}");
            failed += 1;
            continue;
        }
        let digest: String = Sha256::digest(&contents).iter().map(|b| format!("{b:02x}")).collect();
        println!("{}\t{digest}\t{path}", contents.len());
    }
    eprintln!("{} extracted, {failed} failed", paths.len() - failed);
    if failed == 0 { ExitCode::SUCCESS } else { ExitCode::from(1) }
}
