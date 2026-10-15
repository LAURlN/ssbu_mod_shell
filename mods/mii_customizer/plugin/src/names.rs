//! Display names file, format `mc_names 1` (0.5.2): the literal name of a preset's character,
//! used to show the current choice on the rows of the main page ("Stats: Kirby").
//!
//! ```text
//! mc_names 1
//! # comment
//! <preset name: [a-z0-9_]{1,31}> <text: rest of the line, trimmed, 1..40 bytes>
//! ```
//!
//! Optional: without the file, or for a preset without a line, the main page shows the
//! entry text alone, as 0.5.1 did. Text rules are those of a menu entry (`menu::valid_text`);
//! a `#` after the name is part of the text.
//!
//! Pure: no skyline items, no heap, no locks, no panicking paths. Compiled unchanged into the
//! host test (`scratch/2026-10-07_coordinator/names_test.rs`).

use crate::list::{List, MAX_ENTRIES as MAX_LIST_ENTRIES};
use crate::menu::{valid_text, TEXT_BUF, TEXT_MAX};
use crate::preset::{valid_name, Presets, MAX_PRESETS, NAME_BUF};

pub const VERSION_LINE: &str = "mc_names 1";
pub const MAX_FILE: usize = 16 * 1024;
/// A composed row text: entry text, `": "`, name, NUL.
pub const LINE_BUF: usize = TEXT_MAX + 2 + TEXT_MAX + 1;
/// The preset whose name stands for "the Mii's own class" (row 0 of an entry page).
pub const DEFAULT_PRESET: &str = "miigunner";

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum FileState {
    Ok,
    Absent,
    TooLarge,
    BadVersionLine,
}

impl FileState {
    pub fn name(self) -> &'static str {
        match self {
            FileState::Ok => "ok",
            FileState::Absent => "absent",
            FileState::TooLarge => "too_large",
            FileState::BadVersionLine => "bad_version_line",
        }
    }
}

/// Names by preset index; an empty name means "none".
pub struct Names {
    text: [[u8; TEXT_BUF]; MAX_PRESETS],
    len: [u8; MAX_PRESETS],
    default: usize,
}

impl Names {
    pub const fn new() -> Self {
        Names { text: [[0; TEXT_BUF]; MAX_PRESETS], len: [0; MAX_PRESETS], default: MAX_PRESETS }
    }

    /// The name of preset `preset`; empty when it has none.
    pub fn name(&self, preset: usize) -> &[u8] {
        let len = self.len.get(preset).copied().unwrap_or(0) as usize;
        match self.text.get(preset) {
            Some(text) => text.get(..len.min(TEXT_MAX)).unwrap_or(&[]),
            None => &[],
        }
    }

    /// The name shown for "no preset": that of [`DEFAULT_PRESET`]; empty when it has none.
    pub fn default_name(&self) -> &[u8] {
        self.name(self.default)
    }

    /// The name for a choice: the preset's, or the default's for `None`.
    pub fn value(&self, preset: Option<usize>) -> &[u8] {
        match preset {
            Some(preset) => self.name(preset),
            None => self.default_name(),
        }
    }

    /// Sort key for preset `preset`: display name if present, else preset name.
    pub fn sort_key<'a>(
        &'a self,
        preset: Option<usize>,
        presets: &'a Presets,
        buf: &'a mut [u8; NAME_BUF],
    ) -> &'a [u8] {
        match preset {
            Some(p) => {
                let n = self.name(p);
                if !n.is_empty() {
                    n
                } else {
                    let len = presets.name(p, buf);
                    buf.get(..len).unwrap_or(&[])
                }
            }
            None => &[],
        }
    }
}

pub struct Report {
    pub state: FileState,
    pub lines: u32,
    pub accepted: u32,
    pub rejected: u32,
    /// 1-based number of the first rejected line, 0 when none.
    pub first_reject: u32,
}

fn trim(mut s: &[u8]) -> &[u8] {
    while let Some((first, rest)) = s.split_first() {
        if *first == b' ' || *first == b'\t' {
            s = rest;
        } else {
            break;
        }
    }
    while let Some((last, rest)) = s.split_last() {
        if *last == b' ' || *last == b'\t' || *last == b'\r' {
            s = rest;
        } else {
            break;
        }
    }
    s
}

/// Parse a whole file (`None` = the file does not exist). A rejected line (bad or unknown
/// preset name, bad text, second line for a preset) is counted and skipped.
pub fn parse(bytes: Option<&[u8]>, presets: &Presets) -> (Names, Report) {
    let mut names = Names::new();
    let mut report = Report { state: FileState::Ok, lines: 0, accepted: 0, rejected: 0, first_reject: 0 };
    let bytes = match bytes {
        Some(bytes) => bytes,
        None => {
            report.state = FileState::Absent;
            return (names, report);
        }
    };
    if bytes.len() > MAX_FILE {
        report.state = FileState::TooLarge;
        return (names, report);
    }
    let body = match bytes.split_last() {
        Some((b'\n', rest)) => rest,
        _ => bytes,
    };
    let mut number = 0u32;
    for raw in body.split(|b| *b == b'\n') {
        number = number.wrapping_add(1);
        let line = trim(raw);
        if number == 1 {
            if line != VERSION_LINE.as_bytes() || raw.first() != VERSION_LINE.as_bytes().first() {
                report.state = FileState::BadVersionLine;
                report.lines = 1;
                return (Names::new(), report);
            }
            continue;
        }
        if line.is_empty() || line.first() == Some(&b'#') {
            continue;
        }
        let split = line.iter().position(|b| *b == b' ' || *b == b'\t').unwrap_or(line.len());
        let name = line.get(..split).unwrap_or(&[]);
        let text = trim(line.get(split..).unwrap_or(&[]));
        let preset = if valid_name(name) && valid_text(text) { presets.find_name(name) } else { None };
        let stored = match preset {
            Some(preset) if preset < MAX_PRESETS && names.name(preset).is_empty() => {
                if let (Some(slot), Some(len)) = (names.text.get_mut(preset), names.len.get_mut(preset)) {
                    for (dst, src) in slot.iter_mut().zip(text.iter()) {
                        *dst = *src;
                    }
                    *len = text.len() as u8;
                    true
                } else {
                    false
                }
            }
            _ => false,
        };
        if stored {
            report.accepted += 1;
        } else {
            report.rejected = report.rejected.wrapping_add(1);
            if report.first_reject == 0 {
                report.first_reject = number;
            }
        }
    }
    report.lines = number;
    names.default = presets.find_name(DEFAULT_PRESET.as_bytes()).unwrap_or(MAX_PRESETS);
    (names, report)
}

/// `"<text>: <value>"` as a C string; `text` alone when `value` is empty. Both are cut to
/// [`TEXT_MAX`] bytes (they are never longer when they come from the parsers). The buffer
/// always ends with a NUL.
pub fn compose(out: &mut [u8; LINE_BUF], text: &[u8], value: &[u8]) -> usize {
    *out = [0; LINE_BUF];
    let text = text.get(..text.len().min(TEXT_MAX)).unwrap_or(&[]);
    let value = value.get(..value.len().min(TEXT_MAX)).unwrap_or(&[]);
    let sep: &[u8] = if value.is_empty() { b"" } else { b": " };
    let mut at = 0;
    for b in text.iter().chain(sep.iter()).chain(value.iter()) {
        if at + 1 >= LINE_BUF {
            break;
        }
        if let Some(slot) = out.get_mut(at) {
            *slot = *b;
            at += 1;
        }
    }
    at
}

/// Compare two byte slices case-insensitively using ASCII folding.
pub fn cmp_ascii_ci(a: &[u8], b: &[u8]) -> core::cmp::Ordering {
    let min_len = a.len().min(b.len());
    let mut i = 0;
    while i < min_len {
        let ca = a[i].to_ascii_lowercase();
        let cb = b[i].to_ascii_lowercase();
        if ca != cb {
            return ca.cmp(&cb);
        }
        i += 1;
    }
    a.len().cmp(&b.len())
}

/// Compute 1-based entry order sorted alphabetically by name (display name or preset name).
/// `out[0..list.len()]` will hold the 1-based logical entry indices (1..=list.len()).
pub fn compute_name_order(
    list: &List,
    names: &Names,
    presets: &Presets,
    out: &mut [u32; MAX_LIST_ENTRIES],
) -> usize {
    let count = list.len();
    let mut i = 0;
    while i < count {
        if let Some(slot) = out.get_mut(i) {
            *slot = (i + 1) as u32;
        }
        i += 1;
    }
    let slice = match out.get_mut(..count) {
        Some(s) => s,
        None => return 0,
    };
    let mut i = 1;
    let mut buf_a = [0u8; NAME_BUF];
    let mut buf_b = [0u8; NAME_BUF];
    while i < count {
        let mut j = i;
        while j > 0 {
            let a = slice[j - 1]; // 1-based
            let b = slice[j];     // 1-based
            let preset_a = list.preset(a as usize - 1);
            let preset_b = list.preset(b as usize - 1);
            let key_a = names.sort_key(preset_a, presets, &mut buf_a);
            let key_b = names.sort_key(preset_b, presets, &mut buf_b);
            let ord = cmp_ascii_ci(key_a, key_b).then_with(|| a.cmp(&b));
            if ord == core::cmp::Ordering::Greater {
                slice.swap(j - 1, j);
                j -= 1;
            } else {
                break;
            }
        }
        i += 1;
    }
    count
}
