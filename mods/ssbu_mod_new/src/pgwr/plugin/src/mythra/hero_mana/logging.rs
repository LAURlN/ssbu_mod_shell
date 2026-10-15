//! Crash-tail logging for the owned mana meter.
//!
//! Rule 25: anything that can crash gets a file log, because Skyline's TCP log
//! loses its tail. Two properties matter here and are the reason this is its own
//! file and not `crate::article::log`:
//!
//! * **never per frame.** Every caller logs an *event* (a cast, a spend, a
//!   refusal, a recovery grant, a reset, and one rate line per 60 frames). The
//!   per-frame path in `super::line` logs nothing.
//! * **bounded.** The line count is capped for the life of the process. A long
//!   training session can emit thousands of events; the cap keeps the file from
//!   filling the card, and says so once when it trips rather than going quiet.
//!
//! No file handle and no lock is held across a game call: each line opens,
//! appends, flushes and closes, exactly like `hero_side_b::logging`.
use std::io::Write;
use std::sync::atomic::{AtomicI32, Ordering};

const PATH: &str = "sd:/ultimate/pgwr_mana_log.txt";

/// Lines after which this process stops writing, plus room for the notice.
const BUDGET: i32 = 4000;

static WRITTEN: AtomicI32 = AtomicI32::new(0);

pub(super) fn log(message: impl AsRef<str>) {
    let n = WRITTEN.fetch_add(1, Ordering::Relaxed);
    if n >= BUDGET {
        if n == BUDGET {
            // One line, once, so a truncated log is never mistaken for a quiet
            // one.
            write_line("BUDGET reached; later events are not written");
        }
        return;
    }
    write_line(message.as_ref());
}

fn write_line(body: &str) {
    if let Ok(mut file) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(PATH)
    {
        let _ = writeln!(file, "[PGWR-MANA] {}", body);
        let _ = file.flush();
    }
}
