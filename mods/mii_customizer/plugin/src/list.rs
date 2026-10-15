//! Character list file, format `mc_list 1` (contract F of `prompts/P10-UI-SLICE.md`): which
//! presets the in-game list shows, in which order, and under which message label.
//!
//! ```text
//! mc_list 1
//! # comment
//! <preset name: [a-z0-9_]{1,31}> <message label: [a-z0-9_]{1,63}>
//! ```
//!
//! Pure: no skyline items, no heap, no locks, no panicking paths. The parser returns a plain
//! fixed-size [`List`]; the plugin stores it once at load, before any hook exists, and only
//! reads it afterwards. Compiled unchanged into the host test
//! (`scratch/2026-10-05_P10-UI-SLICE/host_test.rs`).

use crate::preset::{valid_name, Presets, NAME_BUF};

pub const VERSION_LINE: &str = "mc_list 1";
/// Largest accepted file. A longer file is treated like a bad first line.
pub const MAX_FILE: usize = 16 * 1024;
pub const MAX_ENTRIES: usize = 128;
pub const LABEL_MAX: usize = 63;
/// Label buffer: [`LABEL_MAX`] bytes and at least one NUL.
pub const LABEL_BUF: usize = LABEL_MAX + 1;
/// Label family used when the file is absent or its first line is bad:
/// `nam_chr1_00_<preset name>` (107 such labels are in `ui/message/msg_name.msbt`).
pub const DEFAULT_PREFIX: &str = "nam_chr1_00_";
/// Rejected lines remembered for the log; further ones are only counted.
pub const REJECT_LOG_LIMIT: usize = 32;

/// Why one line was ignored.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Reject {
    /// Not exactly two fields.
    FieldCount,
    /// The first field is not `[a-z0-9_]{1,31}`.
    BadName,
    /// The preset is not in the loaded preset file.
    UnknownPreset,
    /// The preset already has a line; the first one stays.
    DupPreset,
    /// The second field is not `[a-z0-9_]{1,63}`.
    BadLabel,
    /// A 129th entry.
    TooManyEntries,
}

impl Reject {
    pub fn name(self) -> &'static str {
        match self {
            Reject::FieldCount => "field_count",
            Reject::BadName => "bad_name",
            Reject::UnknownPreset => "unknown_preset",
            Reject::DupPreset => "dup_preset",
            Reject::BadLabel => "bad_label",
            Reject::TooManyEntries => "too_many_entries",
        }
    }
}

/// Result for the file as a whole. Everything except `Ok` gives the fallback list.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum FileState {
    Ok,
    Absent,
    TooLarge,
    /// The first line is not exactly `mc_list 1`.
    BadVersionLine,
    /// As above, and the file starts with a UTF-8 byte order mark.
    BadVersionLineBom,
}

impl FileState {
    pub fn name(self) -> &'static str {
        match self {
            FileState::Ok => "ok",
            FileState::Absent => "absent",
            FileState::TooLarge => "too_large",
            FileState::BadVersionLine => "bad_version_line",
            FileState::BadVersionLineBom => "bad_version_line_bom",
        }
    }
}

/// One list row: a preset index and the message label shown for it.
#[derive(Clone, Copy)]
pub struct Item {
    preset: u16,
    len: u8,
    label: [u8; LABEL_BUF],
}

const ITEM_EMPTY: Item = Item { preset: 0, len: 0, label: [0; LABEL_BUF] };

/// The list in display order: at most [`MAX_ENTRIES`] entries, no preset twice.
pub struct List {
    items: [Item; MAX_ENTRIES],
    count: usize,
}

impl List {
    pub const fn new() -> Self {
        List { items: [ITEM_EMPTY; MAX_ENTRIES], count: 0 }
    }

    pub fn len(&self) -> usize {
        self.count.min(MAX_ENTRIES)
    }

    /// Preset index of entry `index`.
    pub fn preset(&self, index: usize) -> Option<usize> {
        if index >= self.len() {
            return None;
        }
        self.items.get(index).map(|item| item.preset as usize)
    }

    /// Message label of entry `index`; empty when there is no such entry.
    pub fn label(&self, index: usize) -> &[u8] {
        if index >= self.len() {
            return &[];
        }
        match self.items.get(index) {
            Some(item) => item.label.get(..(item.len as usize).min(LABEL_MAX)).unwrap_or(&[]),
            None => &[],
        }
    }

    /// Entry that shows preset `preset`.
    pub fn find_preset(&self, preset: usize) -> Option<usize> {
        self.items.iter().take(self.len()).position(|item| item.preset as usize == preset)
    }

    fn push(&mut self, preset: usize, label: &[u8]) -> Result<(), Reject> {
        if self.find_preset(preset).is_some() {
            return Err(Reject::DupPreset);
        }
        if !valid_label(label) || preset > u16::MAX as usize {
            return Err(Reject::BadLabel);
        }
        let count = self.len();
        let slot = match self.items.get_mut(count) {
            Some(slot) => slot,
            None => return Err(Reject::TooManyEntries),
        };
        *slot = ITEM_EMPTY;
        slot.preset = preset as u16;
        slot.len = label.len() as u8;
        for (dst, src) in slot.label.iter_mut().zip(label.iter()) {
            *dst = *src;
        }
        self.count = count + 1;
        Ok(())
    }
}

/// `[a-z0-9_]{1,63}`.
pub fn valid_label(label: &[u8]) -> bool {
    !label.is_empty()
        && label.len() <= LABEL_MAX
        && label.iter().all(|b| matches!(*b, b'a'..=b'z' | b'0'..=b'9' | b'_'))
}

/// What the parser saw, for the load-time log.
pub struct Report {
    pub state: FileState,
    /// True when the list is "all loaded presets in file order" instead of the file's.
    pub fallback: bool,
    /// Lines in the file, the version line included.
    pub lines: u32,
    pub accepted: u32,
    pub rejected: u32,
    rejects: [(u32, Reject); REJECT_LOG_LIMIT],
    kept: usize,
}

impl Report {
    pub const fn new() -> Self {
        Report {
            state: FileState::Ok,
            fallback: false,
            lines: 0,
            accepted: 0,
            rejected: 0,
            rejects: [(0, Reject::FieldCount); REJECT_LOG_LIMIT],
            kept: 0,
        }
    }

    /// The first [`REJECT_LOG_LIMIT`] rejected lines as (1-based line number, reason).
    pub fn rejects(&self) -> &[(u32, Reject)] {
        self.rejects.get(..self.kept).unwrap_or(&[])
    }

    fn reject(&mut self, line: u32, why: Reject) {
        self.rejected = self.rejected.wrapping_add(1);
        if let Some(slot) = self.rejects.get_mut(self.kept) {
            *slot = (line, why);
            self.kept += 1;
        }
    }
}

fn strip_cr(line: &[u8]) -> &[u8] {
    match line.split_last() {
        Some((b'\r', rest)) => rest,
        _ => line,
    }
}

/// Every loaded preset in file order, labelled `nam_chr1_00_<name>`.
pub fn fallback(presets: &Presets) -> List {
    let mut list = List::new();
    let mut preset = 0;
    while preset < presets.len() {
        let mut name = [0u8; NAME_BUF];
        let len = presets.name(preset, &mut name);
        let mut label = [0u8; LABEL_BUF];
        let mut at = 0;
        for b in DEFAULT_PREFIX.as_bytes().iter().chain(name.iter().take(len)) {
            if let Some(slot) = label.get_mut(at) {
                *slot = *b;
                at += 1;
            }
        }
        if len != 0 {
            // A full list or an unusable name leaves the preset out; nothing else can fail.
            let _ = list.push(preset, label.get(..at.min(LABEL_MAX)).unwrap_or(&[]));
        }
        preset += 1;
    }
    list
}

/// Parse a whole file (`None` = the file does not exist). Lines end with `\n` or `\r\n`.
/// On any state other than [`FileState::Ok`] the result is [`fallback`]. `presets` gives the
/// names a line may use.
///
/// The file is read as bytes: everything the format means is ASCII, so a non-ASCII byte in
/// a comment is harmless and one in a field makes that field invalid.
pub fn parse(bytes: Option<&[u8]>, presets: &Presets) -> (List, Report) {
    let mut report = Report::new();
    let bytes = match bytes {
        Some(bytes) => bytes,
        None => {
            report.state = FileState::Absent;
            report.fallback = true;
            return (fallback(presets), report);
        }
    };
    if bytes.len() > MAX_FILE {
        report.state = FileState::TooLarge;
        report.fallback = true;
        return (fallback(presets), report);
    }
    let mut list = List::new();
    // A final newline does not start another line.
    let body = match bytes.split_last() {
        Some((b'\n', rest)) => rest,
        _ => bytes,
    };
    let mut number = 0u32;
    for raw in body.split(|b| *b == b'\n') {
        number = number.wrapping_add(1);
        let line = strip_cr(raw);
        if number == 1 {
            if line != VERSION_LINE.as_bytes() {
                report.state = if line.starts_with(&[0xef, 0xbb, 0xbf]) {
                    FileState::BadVersionLineBom
                } else {
                    FileState::BadVersionLine
                };
                report.lines = 1;
                report.fallback = true;
                return (fallback(presets), report);
            }
            continue;
        }
        let text = line.split(|b| *b == b'#').next().unwrap_or(&[]);
        let mut fields = text.split(|b| *b == b' ' || *b == b'\t').filter(|f| !f.is_empty());
        let name = match fields.next() {
            Some(name) => name,
            None => continue,
        };
        let stored = match (fields.next(), fields.next()) {
            (Some(label), None) => {
                if !valid_name(name) {
                    Err(Reject::BadName)
                } else if !valid_label(label) {
                    Err(Reject::BadLabel)
                } else {
                    match presets.find_name(name) {
                        None => Err(Reject::UnknownPreset),
                        Some(preset) => list.push(preset, label),
                    }
                }
            }
            _ => Err(Reject::FieldCount),
        };
        match stored {
            Ok(()) => report.accepted += 1,
            Err(why) => report.reject(number, why),
        }
    }
    report.lines = number;
    (list, report)
}
