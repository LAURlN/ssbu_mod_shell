//! Menu file, format `mc_menu 1` (contract G of `prompts/P11-MENU.md`), and the pages of
//! mod mode (contract M): which rows a page has, which of them can be decided, where the
//! cursor and the tick start, and what a finished page leads to.
//!
//! ```text
//! mc_menu 1
//! # comment
//! entry <id: [a-z0-9_]{1,31}> <kind: stats|slot> <text: rest of the line, 1..40 bytes>
//! label <id> <message label: [a-z0-9_]{1,63}>
//! allow <id> <preset name>
//! ```
//!
//! A `label` or `allow` line names an entry that an earlier line defined. A `#` starts a
//! comment at the start of a line and after the fields of a `label` / `allow` line; in an
//! `entry` line the text is everything after the kind, so it may contain `#`.
//!
//! Pure: no skyline items, no heap, no locks, no panicking paths. Compiled unchanged into
//! the host test (`scratch/2026-10-06_P11-MENU/host_test.rs`).

use crate::list::{valid_label, List, LABEL_BUF, LABEL_MAX};
use crate::preset::{valid_name, Presets, MAX_PRESETS};
use crate::ui::{self, Action, Outcome};

pub const VERSION_LINE: &str = "mc_menu 1";
/// Largest accepted file. A longer file is treated like a bad first line.
pub const MAX_FILE: usize = 16 * 1024;
pub const MAX_ENTRIES: usize = 48;
pub const ID_MAX: usize = 31;
pub const ID_BUF: usize = ID_MAX + 1;
pub const TEXT_MAX: usize = 40;
/// Text buffer: [`TEXT_MAX`] bytes and at least one NUL (the game's setter takes a C string).
pub const TEXT_BUF: usize = TEXT_MAX + 1;
/// Rejected lines remembered for the log; further ones are only counted.
pub const REJECT_LOG_LIMIT: usize = 32;
/// Row 0 of an entry page: the Mii's own class (contract M2).
pub const DEFAULT_LABEL: &str = "nam_chr1_00_miigunner";
const ALLOW_WORDS: usize = (MAX_PRESETS + 63) / 64;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Kind {
    /// The character stat preset of the Mii (what 0.4.0 offered).
    Stats,
    /// A move slot: a row is available only with an `allow` line.
    Slot,
    /// An option page: this entry's own choices.
    Option,
}

impl Kind {
    pub fn name(self) -> &'static str {
        match self {
            Kind::Stats => "stats",
            Kind::Slot => "slot",
            Kind::Option => "option",
        }
    }
}

/// Why one line was ignored.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Reject {
    /// The first word is not `entry`, `label` or `allow`.
    UnknownWord,
    /// A field is missing, or a `label` / `allow` line has more than two.
    FieldCount,
    /// The id is not `[a-z0-9_]{1,31}`.
    BadId,
    /// The id already has an `entry` line; the first one stays.
    DupId,
    /// The kind is not `stats` or `slot`.
    BadKind,
    /// The text is empty, longer than 40 bytes, not UTF-8, or has a character the game's
    /// text setter cannot take (a control character, or one outside the 16-bit range).
    BadText,
    /// A second `stats` entry.
    SecondStats,
    /// A 49th entry.
    TooManyEntries,
    /// `label` / `allow` for an id without an earlier `entry` line.
    UnknownId,
    /// The label is not `[a-z0-9_]{1,63}`.
    BadLabel,
    /// The entry already has a label; the first one stays.
    DupLabel,
    /// The preset name is not `[a-z0-9_]{1,31}`.
    BadName,
    /// The preset is not in the loaded preset file.
    UnknownPreset,
    /// `allow` for the `stats` entry (all its rows are available anyway).
    NotSlot,
    /// The entry already allows this preset.
    DupAllow,
    /// `option` for an entry that is not kind `option`.
    NotOption,
    /// The option id is not `[a-z0-9_]{1,31}`.
    BadOptionId,
    /// The entry already has an option with this id.
    DupOptionId,
    /// More than 32 options for an entry.
    TooManyOptions,
    /// An entry of kind `option` had no valid option lines.
    NoOptions,
    /// An allow line for a move that is not implemented.
    Unimplemented,
}

impl Reject {
    pub fn name(self) -> &'static str {
        match self {
            Reject::UnknownWord => "unknown_word",
            Reject::FieldCount => "field_count",
            Reject::BadId => "bad_id",
            Reject::DupId => "dup_id",
            Reject::BadKind => "bad_kind",
            Reject::BadText => "bad_text",
            Reject::SecondStats => "second_stats",
            Reject::TooManyEntries => "too_many_entries",
            Reject::UnknownId => "unknown_id",
            Reject::BadLabel => "bad_label",
            Reject::DupLabel => "dup_label",
            Reject::BadName => "bad_name",
            Reject::UnknownPreset => "unknown_preset",
            Reject::NotSlot => "not_slot",
            Reject::DupAllow => "dup_allow",
            Reject::NotOption => "not_option",
            Reject::BadOptionId => "bad_option_id",
            Reject::DupOptionId => "dup_option_id",
            Reject::TooManyOptions => "too_many_options",
            Reject::NoOptions => "no_options",
            Reject::Unimplemented => "unimplemented",
        }
    }
}

/// Result for the file as a whole. Everything except `Ok` gives an empty menu, which makes
/// mod mode open the character list directly, as 0.4.0 did.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum FileState {
    Ok,
    Absent,
    TooLarge,
    /// The first line is not exactly `mc_menu 1`.
    BadVersionLine,
    /// As above, and the file starts with a UTF-8 byte order mark.
    BadVersionLineBom,
    /// The first line is right and no `entry` line was accepted.
    NoEntry,
}

impl FileState {
    pub fn name(self) -> &'static str {
        match self {
            FileState::Ok => "ok",
            FileState::Absent => "absent",
            FileState::TooLarge => "too_large",
            FileState::BadVersionLine => "bad_version_line",
            FileState::BadVersionLineBom => "bad_version_line_bom",
            FileState::NoEntry => "no_entry",
        }
    }
}

pub const MAX_OPTIONS: usize = 32;

/// One option of an option entry.
#[derive(Clone, Copy)]
pub struct OptionItem {
    id: [u8; ID_BUF],
    id_len: u8,
    text: [u8; TEXT_BUF],
    text_len: u8,
}

const OPTION_EMPTY: OptionItem = OptionItem {
    id: [0; ID_BUF],
    id_len: 0,
    text: [0; TEXT_BUF],
    text_len: 0,
};

impl OptionItem {
    pub fn id(&self) -> &[u8] {
        self.id.get(..(self.id_len as usize).min(ID_MAX)).unwrap_or(&[])
    }

    pub fn text(&self) -> &[u8] {
        self.text.get(..(self.text_len as usize).min(TEXT_MAX)).unwrap_or(&[])
    }

    pub fn text_c(&self) -> &[u8; TEXT_BUF] {
        &self.text
    }
}

/// One menu entry.
#[derive(Clone, Copy)]
pub struct Entry {
    id: [u8; ID_BUF],
    id_len: u8,
    kind: Kind,
    text: [u8; TEXT_BUF],
    text_len: u8,
    label: [u8; LABEL_BUF],
    label_len: u8,
    /// Bit `p`: preset index `p` is available on this slot entry's page.
    allow: [u64; ALLOW_WORDS],
    options: [OptionItem; MAX_OPTIONS],
    options_len: u8,
    line_number: u32,
}

const ENTRY_EMPTY: Entry = Entry {
    id: [0; ID_BUF],
    id_len: 0,
    kind: Kind::Slot,
    text: [0; TEXT_BUF],
    text_len: 0,
    label: [0; LABEL_BUF],
    label_len: 0,
    allow: [0; ALLOW_WORDS],
    options: [OPTION_EMPTY; MAX_OPTIONS],
    options_len: 0,
    line_number: 0,
};

impl Entry {
    pub fn id(&self) -> &[u8] {
        self.id.get(..(self.id_len as usize).min(ID_MAX)).unwrap_or(&[])
    }

    pub fn kind(&self) -> Kind {
        self.kind
    }

    /// The literal text, without its terminator.
    pub fn text(&self) -> &[u8] {
        self.text.get(..(self.text_len as usize).min(TEXT_MAX)).unwrap_or(&[])
    }

    /// The literal text followed by at least one NUL byte.
    pub fn text_c(&self) -> &[u8; TEXT_BUF] {
        &self.text
    }

    /// The fallback message label; empty when the file gives none.
    pub fn label(&self) -> &[u8] {
        self.label.get(..(self.label_len as usize).min(LABEL_MAX)).unwrap_or(&[])
    }

    pub fn allows(&self, preset: usize) -> bool {
        match self.allow.get(preset / 64) {
            Some(word) if preset < MAX_PRESETS => word & (1u64 << (preset % 64)) != 0,
            _ => false,
        }
    }

    /// Number of presets this entry allows.
    pub fn allowed(&self) -> u32 {
        self.allow.iter().map(|w| w.count_ones()).sum()
    }

    pub fn options_len(&self) -> usize {
        self.options_len as usize
    }

    pub fn option(&self, index: usize) -> Option<&OptionItem> {
        if index < self.options_len() {
            self.options.get(index)
        } else {
            None
        }
    }

    pub fn find_option(&self, id: &[u8]) -> Option<usize> {
        self.options.iter().take(self.options_len()).position(|opt| opt.id() == id)
    }

    fn push_option(&mut self, opt_id: &[u8], text: &[u8]) -> Result<(), Reject> {
        if !valid_id(opt_id) {
            return Err(Reject::BadOptionId);
        }
        if !valid_text(text) {
            return Err(Reject::BadText);
        }
        if self.find_option(opt_id).is_some() {
            return Err(Reject::DupOptionId);
        }
        let count = self.options_len();
        if count >= MAX_OPTIONS {
            return Err(Reject::TooManyOptions);
        }
        let slot = match self.options.get_mut(count) {
            Some(s) => s,
            None => return Err(Reject::TooManyOptions),
        };
        *slot = OPTION_EMPTY;
        slot.id_len = opt_id.len() as u8;
        for (dst, src) in slot.id.iter_mut().zip(opt_id.iter()) {
            *dst = *src;
        }
        slot.text_len = text.len() as u8;
        for (dst, src) in slot.text.iter_mut().zip(text.iter()) {
            *dst = *src;
        }
        self.options_len = (count + 1) as u8;
        Ok(())
    }
}

/// The menu in file order: at most [`MAX_ENTRIES`] entries, no id twice, at most one
/// `stats` entry. Empty = no menu.
pub struct Menu {
    entries: [Entry; MAX_ENTRIES],
    count: usize,
}

impl Menu {
    pub const fn new() -> Self {
        Menu { entries: [ENTRY_EMPTY; MAX_ENTRIES], count: 0 }
    }

    /// An empty Menu on the heap, initialised in place. A Menu is far larger than the
    /// 64 KiB stack the plugin is loaded on (session 4 boot crash), so one is never built
    /// or moved as a value: every producer returns the box.
    pub fn boxed() -> Box<Menu> {
        use std::alloc::{alloc, handle_alloc_error, Layout};
        let layout = Layout::new::<Menu>();
        unsafe {
            let p = alloc(layout) as *mut Menu;
            if p.is_null() {
                handle_alloc_error(layout);
            }
            let entries = core::ptr::addr_of_mut!((*p).entries) as *mut Entry;
            let mut i = 0;
            while i < MAX_ENTRIES {
                entries.add(i).write(ENTRY_EMPTY);
                i += 1;
            }
            core::ptr::addr_of_mut!((*p).count).write(0);
            Box::from_raw(p)
        }
    }

    pub fn len(&self) -> usize {
        self.count.min(MAX_ENTRIES)
    }

    pub fn entry(&self, index: usize) -> Option<&Entry> {
        if index >= self.len() {
            return None;
        }
        self.entries.get(index)
    }

    pub fn find_id(&self, id: &[u8]) -> Option<usize> {
        self.entries.iter().take(self.len()).position(|e| e.id() == id)
    }

    fn has_stats(&self) -> bool {
        self.entries.iter().take(self.len()).any(|e| e.kind == Kind::Stats)
    }

    fn push(&mut self, id: &[u8], kind: Kind, text: &[u8], line: u32) -> Result<(), Reject> {
        if !valid_id(id) {
            return Err(Reject::BadId);
        }
        if !valid_text(text) {
            return Err(Reject::BadText);
        }
        if self.find_id(id).is_some() {
            return Err(Reject::DupId);
        }
        if kind == Kind::Stats && self.has_stats() {
            return Err(Reject::SecondStats);
        }
        let count = self.len();
        let slot = match self.entries.get_mut(count) {
            Some(slot) => slot,
            None => return Err(Reject::TooManyEntries),
        };
        *slot = ENTRY_EMPTY;
        slot.kind = kind;
        slot.line_number = line;
        slot.id_len = id.len() as u8;
        for (dst, src) in slot.id.iter_mut().zip(id.iter()) {
            *dst = *src;
        }
        slot.text_len = text.len() as u8;
        for (dst, src) in slot.text.iter_mut().zip(text.iter()) {
            *dst = *src;
        }
        self.count = count + 1;
        Ok(())
    }

    fn add_option(&mut self, id: &[u8], opt_id: &[u8], text: &[u8]) -> Result<(), Reject> {
        if !valid_id(id) {
            return Err(Reject::BadId);
        }
        let index = self.find_id(id).ok_or(Reject::UnknownId)?;
        let slot = self.entries.get_mut(index).ok_or(Reject::UnknownId)?;
        if slot.kind != Kind::Option {
            return Err(Reject::NotOption);
        }
        slot.push_option(opt_id, text)
    }

    fn set_label(&mut self, id: &[u8], label: &[u8]) -> Result<(), Reject> {
        if !valid_id(id) {
            return Err(Reject::BadId);
        }
        if !valid_label(label) {
            return Err(Reject::BadLabel);
        }
        let index = self.find_id(id).ok_or(Reject::UnknownId)?;
        let slot = self.entries.get_mut(index).ok_or(Reject::UnknownId)?;
        if slot.kind == Kind::Option {
            return Err(Reject::BadKind);
        }
        if slot.label_len != 0 {
            return Err(Reject::DupLabel);
        }
        slot.label_len = label.len() as u8;
        for (dst, src) in slot.label.iter_mut().zip(label.iter()) {
            *dst = *src;
        }
        Ok(())
    }

    fn set_allow(
        &mut self,
        id: &[u8],
        name: &[u8],
        presets: &Presets,
        filter_implemented: bool,
    ) -> Result<(), Reject> {
        if !valid_id(id) {
            return Err(Reject::BadId);
        }
        if !valid_name(name) {
            return Err(Reject::BadName);
        }
        let index = self.find_id(id).ok_or(Reject::UnknownId)?;
        let preset = presets.find_name(name).ok_or(Reject::UnknownPreset)?;
        let slot = self.entries.get_mut(index).ok_or(Reject::UnknownId)?;
        if slot.kind != Kind::Slot {
            return Err(Reject::NotSlot);
        }
        if filter_implemented && !is_move_implemented(id, name) {
            return Err(Reject::Unimplemented);
        }
        let word = match slot.allow.get_mut(preset / 64) {
            Some(word) if preset < MAX_PRESETS => word,
            _ => return Err(Reject::UnknownPreset),
        };
        let bit = 1u64 << (preset % 64);
        if *word & bit != 0 {
            return Err(Reject::DupAllow);
        }
        *word |= bit;
        Ok(())
    }
}

pub const IMPLEMENTED_MOVES: [(&[u8], &[u8]); 5] = [
    (b"tilt_side", b"miifighter"),
    (b"tilt_up", b"miifighter"),
    (b"tilt_down", b"miifighter"),
    (b"smash_up", b"fox"),
    (b"aerial_back", b"mario"),
];

pub fn is_move_implemented(entry_id: &[u8], preset_name: &[u8]) -> bool {
    IMPLEMENTED_MOVES.iter().any(|(e, p)| *e == entry_id && *p == preset_name)
}

/// `[a-z0-9_]{1,31}`.
pub fn valid_id(id: &[u8]) -> bool {
    !id.is_empty() && id.len() <= ID_MAX && id.iter().all(|b| matches!(*b, b'a'..=b'z' | b'0'..=b'9' | b'_'))
}

/// 1..=40 bytes of UTF-8 without control characters and without characters above U+FFFF.
/// The game's UTF-8 reader (0x37a22f0) knows one-, two- and three-byte sequences only.
pub fn valid_text(text: &[u8]) -> bool {
    if text.is_empty() || text.len() > TEXT_MAX {
        return false;
    }
    match core::str::from_utf8(text) {
        Ok(s) => s.chars().all(|c| {
            let c = c as u32;
            c >= 0x20 && c != 0x7f && !(0x80..0xa0).contains(&c) && c <= 0xffff
        }),
        Err(_) => false,
    }
}

/// What the parser saw, for the load-time log.
pub struct Report {
    pub state: FileState,
    /// Lines in the file, the version line included.
    pub lines: u32,
    /// Accepted `entry`, `label` and `allow` lines.
    pub entries: u32,
    pub labels: u32,
    pub allows: u32,
    pub options: u32,
    pub rejected: u32,
    rejects: [(u32, Reject); REJECT_LOG_LIMIT],
    kept: usize,
}

impl Report {
    pub const fn new() -> Self {
        Report {
            state: FileState::Ok,
            lines: 0,
            entries: 0,
            labels: 0,
            allows: 0,
            options: 0,
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

fn blank(b: u8) -> bool {
    b == b' ' || b == b'\t'
}

fn trim(mut text: &[u8]) -> &[u8] {
    while let Some((first, rest)) = text.split_first() {
        if !blank(*first) {
            break;
        }
        text = rest;
    }
    while let Some((last, rest)) = text.split_last() {
        if !blank(*last) {
            break;
        }
        text = rest;
    }
    text
}

/// The first blank-separated word of `text` and what follows it (untrimmed).
fn word(text: &[u8]) -> (&[u8], &[u8]) {
    let text = trim(text);
    let end = text.iter().position(|b| blank(*b)).unwrap_or(text.len());
    (text.get(..end).unwrap_or(&[]), text.get(end..).unwrap_or(&[]))
}

pub fn parse_filtered(bytes: Option<&[u8]>, presets: &Presets, moves_active: bool) -> (Box<Menu>, Report) {
    parse_internal(bytes, presets, moves_active, true)
}

/// Parse a whole file (`None` = the file does not exist). Lines end with `\n` or `\r\n`.
/// On any state other than [`FileState::Ok`] the menu is empty. `presets` gives the names
/// an `allow` line may use.
pub fn parse(bytes: Option<&[u8]>, presets: &Presets) -> (Box<Menu>, Report) {
    parse_internal(bytes, presets, true, false)
}

fn parse_internal(
    bytes: Option<&[u8]>,
    presets: &Presets,
    moves_active: bool,
    filter_implemented: bool,
) -> (Box<Menu>, Report) {
    let mut report = Report::new();
    let mut menu = Menu::boxed();
    let bytes = match bytes {
        Some(bytes) => bytes,
        None => {
            report.state = FileState::Absent;
            return (menu, report);
        }
    };
    if bytes.len() > MAX_FILE {
        report.state = FileState::TooLarge;
        return (menu, report);
    }
    // A final newline does not start another line.
    let body = match bytes.split_last() {
        Some((b'\n', rest)) => rest,
        _ => bytes,
    };
    let mut number = 0u32;
    for raw in body.split(|b| *b == b'\n') {
        number = number.wrapping_add(1);
        let line = match raw.split_last() {
            Some((b'\r', rest)) => rest,
            _ => raw,
        };
        if number == 1 {
            if line != VERSION_LINE.as_bytes() {
                report.state = if line.starts_with(&[0xef, 0xbb, 0xbf]) {
                    FileState::BadVersionLineBom
                } else {
                    FileState::BadVersionLine
                };
                report.lines = 1;
                return (menu, report);
            }
            continue;
        }
        let (first, rest) = word(line);
        if first.is_empty() || first.starts_with(b"#") {
            continue;
        }
        let stored = if first == b"entry" {
            let (id, rest) = word(rest);
            let (kind, rest) = word(rest);
            let text = trim(rest);
            if id.is_empty() || kind.is_empty() || text.is_empty() {
                Err(Reject::FieldCount)
            } else if !valid_id(id) {
                Err(Reject::BadId)
            } else {
                let kind = if kind == b"stats" {
                    Ok(Kind::Stats)
                } else if kind == b"slot" {
                    Ok(Kind::Slot)
                } else if kind == b"option" {
                    Ok(Kind::Option)
                } else {
                    Err(Reject::BadKind)
                };
                kind.and_then(|kind| menu.push(id, kind, text, number)).map(|_| report.entries += 1)
            }
        } else if first == b"option" {
            let (id, rest) = word(rest);
            let (opt_id, rest) = word(rest);
            let text = trim(rest);
            if id.is_empty() || opt_id.is_empty() || text.is_empty() {
                Err(Reject::FieldCount)
            } else {
                menu.add_option(id, opt_id, text).map(|_| report.options += 1)
            }
        } else if first == b"label" || first == b"allow" {
            let fields = rest.split(|b| *b == b'#').next().unwrap_or(&[]);
            let (id, fields) = word(fields);
            let (value, fields) = word(fields);
            if id.is_empty() || value.is_empty() || !trim(fields).is_empty() {
                Err(Reject::FieldCount)
            } else if first == b"label" {
                menu.set_label(id, value).map(|_| report.labels += 1)
            } else {
                if filter_implemented && !moves_active {
                    Err(Reject::Unimplemented)
                } else {
                    menu.set_allow(id, value, presets, filter_implemented).map(|_| report.allows += 1)
                }
            }
        } else {
            Err(Reject::UnknownWord)
        };
        if let Err(why) = stored {
            report.reject(number, why);
        }
    }
    report.lines = number;
    let mut i = 0;
    while i < menu.len() {
        let remove = menu.entries[i].kind == Kind::Option && menu.entries[i].options_len == 0;
        if remove {
            let line = menu.entries[i].line_number;
            report.reject(line, Reject::NoOptions);
            report.entries = report.entries.saturating_sub(1);
            let count = menu.len();
            if let Some(tail) = menu.entries.get_mut(i..count) {
                tail.rotate_left(1);
            }
            if let Some(last) = menu.entries.get_mut(count - 1) {
                *last = ENTRY_EMPTY;
            }
            menu.count -= 1;
        } else {
            i += 1;
        }
    }
    if menu.len() == 0 {
        report.state = FileState::NoEntry;
    }
    (menu, report)
}

// ---------------------------------------------------------------------------
// Pages (contract M)
// ---------------------------------------------------------------------------

/// What the list screen shows.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Page {
    /// No menu: the character list of 0.4.0 (row 0 = no preset), left by any decision.
    Direct,
    /// One row per menu entry.
    Main,
    /// Row 0 = the default, then one row per list entry, for menu entry `.0`.
    Entry(usize),
}

impl Page {
    /// A non-zero number for the page (0 is "no page").
    pub fn code(self) -> u32 {
        match self {
            Page::Direct => 1,
            Page::Main => 2,
            Page::Entry(entry) => 3 + entry.min(MAX_ENTRIES) as u32,
        }
    }

    pub fn from_code(code: u32) -> Option<Page> {
        match code {
            1 => Some(Page::Direct),
            2 => Some(Page::Main),
            c if c >= 3 && c < 3 + MAX_ENTRIES as u32 => Some(Page::Entry((c - 3) as usize)),
            _ => None,
        }
    }
}

/// The page mod mode opens first.
pub fn first_page(menu: &Menu) -> Page {
    if menu.len() == 0 {
        Page::Direct
    } else {
        Page::Main
    }
}

/// Rows of a page; 0 for a page that cannot be shown.
pub fn rows(page: Page, menu: &Menu, list: &List) -> u32 {
    match page {
        Page::Direct => ui::rows(list),
        Page::Main => menu.len() as u32,
        Page::Entry(entry) => match menu.entry(entry) {
            Some(e) if e.kind() == Kind::Option => e.options_len() as u32,
            Some(_) => ui::rows(list),
            None => 0,
        },
    }
}

/// Whether row `row` of the page can be decided. A row that is not there cannot.
pub fn available(page: Page, row: u32, menu: &Menu, list: &List) -> bool {
    if row >= rows(page, menu, list) {
        return false;
    }
    match page {
        Page::Direct | Page::Main => true,
        Page::Entry(entry) => match menu.entry(entry) {
            None => false,
            Some(e) if e.kind() == Kind::Option => row < e.options_len() as u32,
            Some(e) if e.kind() == Kind::Stats => true,
            Some(_) if row == 0 => true,
            Some(e) => match list.preset(row as usize - 1) {
                Some(preset) => e.allows(preset),
                None => false,
            },
        },
    }
}

/// Message label of a row: what the label hook writes. For a main-page row this is the
/// fallback under the literal text.
pub fn row_label<'a>(page: Page, row: u32, menu: &'a Menu, list: &'a List) -> &'a [u8] {
    match page {
        Page::Direct => ui::row_label(row, list),
        Page::Main => match menu.entry(row as usize) {
            Some(e) if !e.label().is_empty() => e.label(),
            _ => ui::UNKNOWN_LABEL.as_bytes(),
        },
        Page::Entry(entry) => match menu.entry(entry) {
            Some(e) if e.kind() == Kind::Option => ui::UNKNOWN_LABEL.as_bytes(),
            _ if row == 0 => DEFAULT_LABEL.as_bytes(),
            _ => ui::row_label(row, list),
        },
    }
}

/// Literal text of a row (NUL-terminated buffer), for the rows that have one.
pub fn row_text<'a>(page: Page, row: u32, menu: &'a Menu) -> Option<&'a [u8; TEXT_BUF]> {
    match page {
        Page::Main => menu.entry(row as usize).map(|e| e.text_c()),
        Page::Entry(entry) => match menu.entry(entry) {
            Some(e) if e.kind() == Kind::Option => e.option(row as usize).map(|opt| opt.text_c()),
            _ => None,
        },
        _ => None,
    }
}

/// Where the cursor and the tick are when a page opens. `tick == ui::NO_ROW`: no row
/// carries the tick.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct Start {
    pub cursor: u32,
    pub tick: u32,
}

/// `preset`: the edited Mii's current preset. `hint`: the row the cursor should return to
/// (the entry a page was left from, or the row of a refused decision).
pub fn start(page: Page, menu: &Menu, list: &List, preset: Option<usize>, hint: Option<u32>) -> Start {
    let count = rows(page, menu, list);
    let hinted = match hint {
        Some(row) if row < count => row,
        _ => 0,
    };
    let stats = || match ui::current_row(preset, list) {
        ui::NO_ROW => Start { cursor: 0, tick: ui::NO_ROW },
        row => Start { cursor: row, tick: row },
    };
    match page {
        Page::Direct => stats(),
        Page::Main => Start { cursor: hinted, tick: ui::NO_ROW },
        Page::Entry(entry) => match menu.entry(entry).map(|e| e.kind()) {
            Some(Kind::Stats) => stats(),
            Some(Kind::Option) => {
                let cur = match hint {
                    Some(row) if row < count => row,
                    _ => 0,
                };
                Start { cursor: cur, tick: cur }
            }
            Some(Kind::Slot) => Start { cursor: hinted, tick: 0 },
            _ => Start { cursor: hinted, tick: 0 },
        },
    }
}

/// What a finished page did, apart from where it leads.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Effect {
    /// Cancelled, or a menu entry was opened.
    Nothing,
    /// A stats row was decided: what [`ui::action`] says (set, clear, unsaved Mii, ...).
    Store(Action),
    /// An available row of a slot page was decided. Nothing is stored in this build.
    SlotChosen { row: u32 },
    /// A row of an option page was decided.
    OptionChosen { entry: usize, option: usize },
    /// An unavailable row was reported as decided. Nothing changes; the page opens again.
    Refused { row: u32 },
}

/// Where a finished page leads: `next == None` leaves mod mode (back to the edit menu),
/// otherwise the page to open and the row its cursor should start on.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct Step {
    pub next: Option<(Page, Option<u32>)>,
    pub effect: Effect,
}

pub fn step(page: Page, outcome: Outcome, saved_id: u32, menu: &Menu, list: &List) -> Step {
    let leave = |effect| Step { next: None, effect };
    match page {
        Page::Direct => match outcome {
            Outcome::Cancel => leave(Effect::Nothing),
            decided => leave(Effect::Store(ui::action(decided, saved_id, list))),
        },
        Page::Main => match outcome {
            Outcome::Decide(row) if menu.entry(row as usize).is_some() => {
                Step { next: Some((Page::Entry(row as usize), None)), effect: Effect::Nothing }
            }
            _ => leave(Effect::Nothing),
        },
        Page::Entry(entry) => {
            let kind = match menu.entry(entry) {
                Some(e) => e.kind(),
                None => return leave(Effect::Nothing),
            };
            let back = Some((Page::Main, Some(entry as u32)));
            match outcome {
                Outcome::Cancel => Step { next: back, effect: Effect::Nothing },
                Outcome::Decide(row) if !available(page, row, menu, list) => {
                    Step { next: Some((page, Some(row))), effect: Effect::Refused { row } }
                }
                Outcome::Decide(row) => match kind {
                    Kind::Stats => Step { next: back, effect: Effect::Store(ui::action(outcome, saved_id, list)) },
                    Kind::Slot => Step { next: back, effect: Effect::SlotChosen { row } },
                    Kind::Option => Step { next: back, effect: Effect::OptionChosen { entry, option: row as usize } },
                },
            }
        }
    }
}

/// Bit `row` set: the row can be decided. Three words cover the 129 rows a page can have.
pub const AVAIL_WORDS: usize = 3;

pub fn available_mask(page: Page, menu: &Menu, list: &List) -> [u64; AVAIL_WORDS] {
    let mut mask = [0u64; AVAIL_WORDS];
    let count = rows(page, menu, list);
    let mut row = 0u32;
    while row < count {
        if available(page, row, menu, list) {
            if let Some(word) = mask.get_mut(row as usize / 64) {
                *word |= 1u64 << (row % 64);
            }
        }
        row += 1;
    }
    mask
}

impl crate::loadout::OptionValidator for Menu {
    fn validate_option(&self, entry_id: &str, option_id: &str) -> Result<(u8, u8), crate::loadout::Reject> {
        let entry_idx = self.find_id(entry_id.as_bytes())
            .ok_or(crate::loadout::Reject::UnknownOptionEntry)?;
        let entry = self.entry(entry_idx)
            .ok_or(crate::loadout::Reject::UnknownOptionEntry)?;
        if entry.kind() != Kind::Option {
            return Err(crate::loadout::Reject::UnknownOptionEntry);
        }
        let opt_idx = entry.find_option(option_id.as_bytes())
            .ok_or(crate::loadout::Reject::UnknownOption)?;
        Ok((entry_idx as u8, opt_idx as u8))
    }

    fn option_names(&self, entry: u8, option: u8) -> Option<(&[u8], &[u8])> {
        let e = self.entry(entry as usize)?;
        let o = e.option(option as usize)?;
        Some((e.id(), o.id()))
    }

    fn validate_slot(&self, entry_id: &str, preset_name: &str, presets: &crate::preset::Presets) -> Result<(u8, usize), crate::loadout::Reject> {
        let entry_idx = self.find_id(entry_id.as_bytes())
            .ok_or(crate::loadout::Reject::UnknownSlotEntry)?;
        let entry = self.entry(entry_idx)
            .ok_or(crate::loadout::Reject::UnknownSlotEntry)?;
        if entry.kind() != Kind::Slot {
            return Err(crate::loadout::Reject::UnknownSlotEntry);
        }
        let preset_idx = presets.find_name(preset_name.as_bytes())
            .ok_or(crate::loadout::Reject::UnknownPreset)?;
        if !is_move_implemented(entry_id.as_bytes(), preset_name.as_bytes()) {
            return Err(crate::loadout::Reject::UnimplementedSlot);
        }
        Ok((entry_idx as u8, preset_idx))
    }

    fn slot_names(&self, entry: u8, _preset: usize) -> Option<(&[u8], &[u8])> {
        let e = self.entry(entry as usize)?;
        if e.kind() != Kind::Slot {
            return None;
        }
        for &(impl_entry, impl_preset) in IMPLEMENTED_MOVES.iter() {
            if impl_entry == e.id() {
                return Some((e.id(), impl_preset));
            }
        }
        None
    }
}

