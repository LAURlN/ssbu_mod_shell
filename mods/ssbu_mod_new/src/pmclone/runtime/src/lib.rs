//! Work in progress: private module residency, not a playable fighter pack.
mod loader;
mod modules;

use std::sync::{Mutex, OnceLock};
use std::io::Write;

static MODULES: OnceLock<Mutex<Vec<loader::LoadedModule>>> = OnceLock::new();

#[skyline::main(name = "pyra_mythra_clone_runtime")]
pub fn main() {
    let _ = std::fs::create_dir_all("sd:/ultimate/pyra_mythra_clone");
    let _ = std::fs::write("sd:/ultimate/pyra_mythra_clone/loader.log", b"PMCLONE private-loader v0.1.0; no CSS registration; gameplay disabled\n");
    log("waiting for game module imports; enter a normal match to load common");
    // Avoid nested LoadModule calls inside an NRO hook's loader lock. The
    // private images are prepared on a worker after their imports are visible.
    if let Err(error) = std::thread::Builder::new().name("pmclone_loader".into()).spawn(run) {
        log(&format!("REFUSED worker: {}", error));
    }
}

fn log(text: &str) {
    skyline::println!("[PMCLONE] {}", text);
    if let Ok(mut file) = std::fs::OpenOptions::new().append(true).create(true)
        .open("sd:/ultimate/pyra_mythra_clone/loader.log") {
        let _ = writeln!(file, "{}", text);
        let _ = file.flush();
    }
}

fn run() {
    let mut ready = false;
    for attempt in 0..600 {
        let missing = modules::MODULES.iter().find_map(|spec| unsafe { loader::LoadedModule::missing_import(spec) });
        if let Some(name) = missing {
            if attempt % 60 == 0 {
                log(&format!("waiting for import {}", String::from_utf8_lossy(&name[..name.len()-1])));
            }
            std::thread::sleep(std::time::Duration::from_millis(500));
        } else {
            ready = true;
            break;
        }
    }
    if !ready { log("REFUSED required game imports not available after 5 minutes"); return; }
    let mut loaded = Vec::new();
    for spec in modules::MODULES {
        match unsafe { loader::LoadedModule::load(spec) } {
            Ok(module) => {
                log(&module.describe());
                if module.factory(0).is_ok() {
                    log("REFUSED factory isolation guard unexpectedly open");
                    return;
                }
                log("factory isolation guard passed: native character imports still block gameplay");
                loaded.push(module);
            }
            Err(error) => {
                log(&format!("REFUSED {}: {}", spec.name, error));
                // No fighter registration or factory calls occur on failure.
                break;
            }
        }
    }
    let complete = loaded.len() == modules::MODULES.len();
    let _ = MODULES.set(Mutex::new(loaded));
    if complete { log("PRIVATE_MODULE_LOAD_CHECK_PASSED: all 27 factories belong to private executable images; no fighter installed"); }
}
