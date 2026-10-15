//! Independent crash-tail logging for the opt-in side-B implementation.
//! No logger lock or open file is retained over a game call.
use std::io::Write;

pub(super) fn log(message: impl AsRef<str>) {
    if let Ok(mut file) = std::fs::OpenOptions::new().create(true).append(true)
        .open("sd:/ultimate/pgwr_hero_s_log.txt") {
        let _ = writeln!(file, "[PGWR-HERO-S] {}", message.as_ref());
        let _ = file.flush();
    }
}
