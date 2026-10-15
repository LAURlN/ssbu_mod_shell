//! Loadout file, versions 1 and 2 (contract B of `prompts/P7-PRESET-ENGINE.md`; version 1
//! is `prompts/P4-OVERRIDE-SLICE.md`).
//!
//! ```text
//! mc_loadouts 2
//! # comment
//! <id: 8 hex digits> preset <preset name>          (version 2 only)
//! <id: 8 hex digits> weight <decimal value>
//! <id: 8 hex digits> walk_speed_max <decimal value>
//! ```
//!
//! Pure: no skyline items, no heap, no locks, no panicking paths. The parser fills a plain
//! [`Table`]; [`serialise`] turns a table back into file text; [`Store`] is the fixed-size
//! copy the hook looks values up in. Compiled unchanged into the host tests
//! (`scratch/2026-10-05_P7-PRESET-ENGINE/host_test.rs`,
//! `scratch/2026-10-05_P10-UI-SLICE/host_test.rs`).
//!
//! 0.4.0 adds the runtime writer [`Store::set_preset`] (the editor UI) and the reader rule
//! B+ of `prompts/P10-UI-SLICE.md` ([`load`]: `loadouts.new` is read when `loadouts.txt`
//! does not exist).

use crate::preset::{Presets, NAME_BUF};
use core::sync::atomic::{AtomicBool, AtomicU32, AtomicU64, AtomicU8, Ordering};

/// Largest accepted file. A longer file disables all overrides.
pub const MAX_FILE: usize = 16 * 1024;
pub const MAX_IDS: usize = 32;
/// Keys with an explicit value line. The index is the field index of the key's hash
/// (`preset::NAMED_HASHES`).
pub const KEYS: usize = 2;
pub const VERSION_LINE_1: &str = "mc_loadouts 1";
pub const VERSION_LINE_2: &str = "mc_loadouts 2";
pub const VERSION_LINE_3: &str = "mc_loadouts 3";
pub const KEY_NAMES: [&str; KEYS] = ["weight", "walk_speed_max"];
pub const PRESET_KEY: &str = "preset";
pub const OPTION_KEY: &str = "option";
pub const SLOT_KEY: &str = "slot";
pub const MAX_LOADOUT_OPTIONS: usize = 16;
pub const MAX_LOADOUT_SLOTS: usize = 16;
pub const ID_BUF: usize = 32;

pub trait OptionValidator {
    fn validate_option(&self, entry_id: &str, option_id: &str) -> Result<(u8, u8), Reject>;
    fn option_names(&self, entry: u8, option: u8) -> Option<(&[u8], &[u8])>;
    fn validate_slot(&self, entry_id: &str, preset_name: &str, presets: &Presets) -> Result<(u8, usize), Reject> {
        let _ = (entry_id, preset_name, presets);
        Err(Reject::UnknownSlotEntry)
    }
    fn slot_names(&self, entry: u8, preset: usize) -> Option<(&[u8], &[u8])> {
        let _ = (entry, preset);
        None
    }
}

pub struct NoOptions;
impl OptionValidator for NoOptions {
    fn validate_option(&self, _entry_id: &str, _option_id: &str) -> Result<(u8, u8), Reject> {
        Err(Reject::UnknownOptionEntry)
    }

    fn option_names(&self, _entry: u8, _option: u8) -> Option<(&[u8], &[u8])> {
        None
    }
}

/// Accepted ranges of explicit values, inclusive. Proposals from the first console test,
/// not declared safe. Preset values are not range-limited.
pub const RANGES: [(f32, f32); KEYS] = [(60.0, 140.0), (0.5, 2.0)];
/// Rejected lines remembered for the log; further ones are only counted.
pub const REJECT_LOG_LIMIT: usize = 32;
const VALUE_MAX_LEN: usize = 24;
const VALUE_MAX_DIGITS: u32 = 18;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct OptionChoice {
    pub entry: u8,
    pub option: u8,
    pub entry_id: [u8; ID_BUF],
    pub entry_len: u8,
    pub option_id: [u8; ID_BUF],
    pub option_len: u8,
}

impl OptionChoice {
    pub fn entry_id(&self) -> &[u8] {
        self.entry_id.get(..(self.entry_len as usize).min(ID_BUF - 1)).unwrap_or(&[])
    }

    pub fn option_id(&self) -> &[u8] {
        self.option_id.get(..(self.option_len as usize).min(ID_BUF - 1)).unwrap_or(&[])
    }
}

const OPTION_CHOICE_EMPTY: OptionChoice = OptionChoice {
    entry: 0,
    option: 0,
    entry_id: [0; ID_BUF],
    entry_len: 0,
    option_id: [0; ID_BUF],
    option_len: 0,
};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct SlotChoice {
    pub entry: u8,
    pub preset: usize,
    pub entry_id: [u8; ID_BUF],
    pub entry_len: u8,
    pub preset_name: [u8; NAME_BUF],
    pub preset_len: u8,
}

impl SlotChoice {
    pub fn entry_id(&self) -> &[u8] {
        self.entry_id.get(..(self.entry_len as usize).min(ID_BUF - 1)).unwrap_or(&[])
    }

    pub fn preset_name(&self) -> &[u8] {
        self.preset_name.get(..(self.preset_len as usize).min(NAME_BUF - 1)).unwrap_or(&[])
    }
}

const SLOT_CHOICE_EMPTY: SlotChoice = SlotChoice {
    entry: 0,
    preset: 0,
    entry_id: [0; ID_BUF],
    entry_len: 0,
    preset_name: [0; NAME_BUF],
    preset_len: 0,
};

/// Why one line was ignored.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Reject {
    NonUtf8,
    FieldCount,
    BadId,
    ZeroId,
    UnknownKey,
    BadValue,
    OutOfRange,
    TooManyIds,
    /// A `preset` line whose name is not `[a-z0-9_]{1,31}`.
    BadName,
    /// A `preset` line whose name is not in the loaded preset file.
    UnknownPreset,
    /// An unknown option entry or not an option entry.
    UnknownOptionEntry,
    /// An unknown option for the entry.
    UnknownOption,
    /// More than 16 options for one ID.
    TooManyOptions,
    /// An unknown slot entry or not a slot entry.
    UnknownSlotEntry,
    /// An unimplemented move choice for a slot.
    UnimplementedSlot,
    /// More than 16 slots for one ID.
    TooManySlots,
}

impl Reject {
    pub fn name(self) -> &'static str {
        match self {
            Reject::NonUtf8 => "non_utf8",
            Reject::FieldCount => "field_count",
            Reject::BadId => "bad_id",
            Reject::ZeroId => "zero_id",
            Reject::UnknownKey => "unknown_key",
            Reject::BadValue => "bad_value",
            Reject::OutOfRange => "out_of_range",
            Reject::TooManyIds => "too_many_ids",
            Reject::BadName => "bad_name",
            Reject::UnknownPreset => "unknown_preset",
            Reject::UnknownOptionEntry => "unknown_option_entry",
            Reject::UnknownOption => "unknown_option",
            Reject::TooManyOptions => "too_many_options",
            Reject::UnknownSlotEntry => "unknown_slot_entry",
            Reject::UnimplementedSlot => "unimplemented_slot",
            Reject::TooManySlots => "too_many_slots",
        }
    }
}

/// Result for the file as a whole. Everything except `Ok` means "no overrides".
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum FileState {
    Ok,
    TooLarge,
    /// The first line is neither `mc_loadouts 1` nor `mc_loadouts 2`.
    BadVersionLine,
    /// As above, and the file starts with a UTF-8 byte order mark.
    BadVersionLineBom,
}

impl FileState {
    pub fn name(self) -> &'static str {
        match self {
            FileState::Ok => "ok",
            FileState::TooLarge => "too_large",
            FileState::BadVersionLine => "bad_version_line",
            FileState::BadVersionLineBom => "bad_version_line_bom",
        }
    }
}

/// Where an applied value came from.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
#[repr(u8)]
pub enum Src {
    /// A `<id> weight|walk_speed_max <v>` line.
    Explicit = 0,
    /// The preset named by the `<id> preset <name>` line.
    Preset = 1,
}

pub const SRC_COUNT: usize = 2;

impl Src {
    pub fn name(self) -> &'static str {
        match self {
            Src::Explicit => "explicit",
            Src::Preset => "preset",
        }
    }
}

#[derive(Clone, Copy, Debug)]
pub struct Entry {
    pub id: u32,
    /// Index into the preset table.
    pub preset: Option<usize>,
    pub has: [bool; KEYS],
    pub value: [f32; KEYS],
    pub options: [OptionChoice; MAX_LOADOUT_OPTIONS],
    pub options_count: u8,
    pub slots: [SlotChoice; MAX_LOADOUT_SLOTS],
    pub slots_count: u8,
}

const ENTRY_EMPTY: Entry = Entry {
    id: 0,
    preset: None,
    has: [false; KEYS],
    value: [0.0; KEYS],
    options: [OPTION_CHOICE_EMPTY; MAX_LOADOUT_OPTIONS],
    options_count: 0,
    slots: [SLOT_CHOICE_EMPTY; MAX_LOADOUT_SLOTS],
    slots_count: 0,
};

impl Entry {
    fn is_empty(&self) -> bool {
        self.preset.is_none() && !self.has.iter().any(|h| *h) && self.options_count == 0 && self.slots_count == 0
    }

    /// Same ID, same preset, same keys, same value bits, same options, same slots.
    fn same(&self, other: &Entry) -> bool {
        self.id == other.id
            && self.preset == other.preset
            && self.has == other.has
            && self
                .has
                .iter()
                .zip(self.value.iter().zip(other.value.iter()))
                .all(|(has, (a, b))| !*has || a.to_bits() == b.to_bits())
            && self.options_count == other.options_count
            && self.options.get(..self.options_count as usize).unwrap_or(&[])
                == other.options.get(..other.options_count as usize).unwrap_or(&[])
            && self.slots_count == other.slots_count
            && self.slots.get(..self.slots_count as usize).unwrap_or(&[])
                == other.slots.get(..other.slots_count as usize).unwrap_or(&[])
    }
}

/// Loadouts in file order: at most [`MAX_IDS`] distinct IDs, none without content.
pub struct Table {
    entries: [Entry; MAX_IDS],
    count: usize,
}

impl PartialEq for Table {
    fn eq(&self, other: &Table) -> bool {
        self.count == other.count && self.entries().iter().zip(other.entries()).all(|(a, b)| a.same(b))
    }
}

impl Table {
    pub const fn new() -> Self {
        Table { entries: [ENTRY_EMPTY; MAX_IDS], count: 0 }
    }

    /// An empty Table on the heap, initialised in place. A Table is far larger than the
    /// 64 KiB stack the plugin is loaded on (session 4 boot crash), so one is never built
    /// or moved as a value: every producer returns the box.
    pub fn boxed() -> Box<Table> {
        use std::alloc::{alloc, handle_alloc_error, Layout};
        let layout = Layout::new::<Table>();
        unsafe {
            let p = alloc(layout) as *mut Table;
            if p.is_null() {
                handle_alloc_error(layout);
            }
            let entries = core::ptr::addr_of_mut!((*p).entries) as *mut Entry;
            let mut i = 0;
            while i < MAX_IDS {
                entries.add(i).write(ENTRY_EMPTY);
                i += 1;
            }
            core::ptr::addr_of_mut!((*p).count).write(0);
            Box::from_raw(p)
        }
    }

    #[allow(dead_code)]
    pub fn len(&self) -> usize {
        self.count
    }

    pub fn entries(&self) -> &[Entry] {
        self.entries.get(..self.count).unwrap_or(&[])
    }

    #[allow(dead_code)]
    pub fn get(&self, id: u32, key: usize) -> Option<f32> {
        let entry = self.entries().iter().find(|e| e.id == id)?;
        if *entry.has.get(key)? {
            entry.value.get(key).copied()
        } else {
            None
        }
    }

    #[allow(dead_code)]
    pub fn preset(&self, id: u32) -> Option<usize> {
        self.entries().iter().find(|e| e.id == id)?.preset
    }

    #[allow(dead_code)]
    pub fn slot_of(&self, id: u32, entry: usize) -> Option<usize> {
        let e = self.entries().iter().find(|e| e.id == id)?;
        let count = e.slots_count as usize;
        e.slots.iter().take(count).find(|s| s.entry as usize == entry).map(|s| s.preset)
    }

    /// The entry for `id`, appended when it is new.
    fn entry_mut(&mut self, id: u32) -> Result<&mut Entry, Reject> {
        let count = self.count;
        let mut at = self.entries.iter().take(count).position(|e| e.id == id);
        if at.is_none() {
            if count >= MAX_IDS {
                return Err(Reject::TooManyIds);
            }
            if let Some(slot) = self.entries.get_mut(count) {
                *slot = ENTRY_EMPTY;
                slot.id = id;
                self.count = count + 1;
                at = Some(count);
            }
        }
        at.and_then(move |i| self.entries.get_mut(i)).ok_or(Reject::TooManyIds)
    }

    /// Store one explicit value. `Ok(true)` when it replaced an earlier value for the same
    /// id+key.
    pub fn set(&mut self, id: u32, key: usize, value: f32) -> Result<bool, Reject> {
        if key >= KEYS {
            return Err(Reject::UnknownKey);
        }
        let entry = self.entry_mut(id)?;
        match (entry.has.get_mut(key), entry.value.get_mut(key)) {
            (Some(has), Some(slot)) => {
                let replaced = *has;
                *has = true;
                *slot = value;
                Ok(replaced)
            }
            _ => Err(Reject::UnknownKey),
        }
    }

    /// Give `id` the preset with index `preset`. `Ok(true)` when it replaced an earlier one.
    pub fn set_preset(&mut self, id: u32, preset: usize) -> Result<bool, Reject> {
        let entry = self.entry_mut(id)?;
        let replaced = entry.preset.is_some();
        entry.preset = Some(preset);
        Ok(replaced)
    }

    /// Store an option choice for `id`. If `option == 0`, remove any choice for `entry`.
    pub fn set_option(
        &mut self,
        id: u32,
        entry: usize,
        option: usize,
        entry_id: &[u8],
        opt_id: &[u8],
    ) -> Result<bool, Reject> {
        let e = self.entry_mut(id)?;
        let count = e.options_count as usize;
        let pos = e.options.iter().take(count).position(|c| c.entry as usize == entry);
        if option == 0 {
            if let Some(pos) = pos {
                if let Some(tail) = e.options.get_mut(pos..count) {
                    tail.rotate_left(1);
                }
                e.options_count = (count - 1) as u8;
                self.clear_entry_if_empty(id);
                Ok(true)
            } else {
                Ok(false)
            }
        } else {
            if let Some(pos) = pos {
                if let Some(slot) = e.options.get_mut(pos) {
                    let replaced = slot.option as usize != option;
                    slot.option = option as u8;
                    slot.entry_len = entry_id.len() as u8;
                    for (dst, src) in slot.entry_id.iter_mut().zip(entry_id.iter()) {
                        *dst = *src;
                    }
                    slot.option_len = opt_id.len() as u8;
                    for (dst, src) in slot.option_id.iter_mut().zip(opt_id.iter()) {
                        *dst = *src;
                    }
                    return Ok(replaced);
                }
            }
            if count >= MAX_LOADOUT_OPTIONS {
                return Err(Reject::TooManyOptions);
            }
            if let Some(slot) = e.options.get_mut(count) {
                let mut choice = OptionChoice {
                    entry: entry as u8,
                    option: option as u8,
                    entry_id: [0; ID_BUF],
                    entry_len: entry_id.len() as u8,
                    option_id: [0; ID_BUF],
                    option_len: opt_id.len() as u8,
                };
                for (dst, src) in choice.entry_id.iter_mut().zip(entry_id.iter()) {
                    *dst = *src;
                }
                for (dst, src) in choice.option_id.iter_mut().zip(opt_id.iter()) {
                    *dst = *src;
                }
                *slot = choice;
                e.options_count = (count + 1) as u8;
            }
            Ok(false)
        }
    }

    pub fn set_option_idx(&mut self, id: u32, entry: usize, option: usize) -> Result<bool, Reject> {
        self.set_option(id, entry, option, &[], &[])
    }

    pub fn set_slot(
        &mut self,
        id: u32,
        entry: usize,
        preset: usize,
        entry_id: &[u8],
        preset_name: &[u8],
    ) -> Result<bool, Reject> {
        let e = self.entry_mut(id)?;
        let count = e.slots_count as usize;
        let pos = e.slots.iter().take(count).position(|s| s.entry as usize == entry);
        if let Some(pos) = pos {
            if let Some(slot) = e.slots.get_mut(pos) {
                let replaced = slot.preset != preset;
                slot.preset = preset;
                slot.entry_len = entry_id.len() as u8;
                for (dst, src) in slot.entry_id.iter_mut().zip(entry_id.iter()) {
                    *dst = *src;
                }
                slot.preset_len = preset_name.len() as u8;
                for (dst, src) in slot.preset_name.iter_mut().zip(preset_name.iter()) {
                    *dst = *src;
                }
                return Ok(replaced);
            }
        }
        if count >= MAX_LOADOUT_SLOTS {
            return Err(Reject::TooManySlots);
        }
        if let Some(slot) = e.slots.get_mut(count) {
            let mut choice = SlotChoice {
                entry: entry as u8,
                preset,
                entry_id: [0; ID_BUF],
                entry_len: entry_id.len() as u8,
                preset_name: [0; NAME_BUF],
                preset_len: preset_name.len() as u8,
            };
            for (dst, src) in choice.entry_id.iter_mut().zip(entry_id.iter()) {
                *dst = *src;
            }
            for (dst, src) in choice.preset_name.iter_mut().zip(preset_name.iter()) {
                *dst = *src;
            }
            *slot = choice;
            e.slots_count = (count + 1) as u8;
        }
        Ok(false)
    }

    pub fn remove_slot(&mut self, id: u32, entry: usize) -> bool {
        let count = self.count;
        let at = match self.entries.iter().take(count).position(|e| e.id == id) {
            Some(at) => at,
            None => return false,
        };
        let e = match self.entries.get_mut(at) {
            Some(e) => e,
            None => return false,
        };
        let sc = e.slots_count as usize;
        if let Some(pos) = e.slots.iter().take(sc).position(|s| s.entry as usize == entry) {
            if let Some(tail) = e.slots.get_mut(pos..sc) {
                tail.rotate_left(1);
            }
            e.slots_count = (sc - 1) as u8;
            self.clear_entry_if_empty(id);
            true
        } else {
            false
        }
    }

    fn clear_entry_if_empty(&mut self, id: u32) {
        let count = self.count;
        let at = match self.entries.iter().take(count).position(|e| e.id == id) {
            Some(at) => at,
            None => return,
        };
        let empty = match self.entries.get(at) {
            Some(entry) => entry.is_empty(),
            None => false,
        };
        if empty {
            if let Some(tail) = self.entries.get_mut(at..count) {
                tail.rotate_left(1);
            }
            self.count = count - 1;
        }
    }

    /// Take the preset of `id` away; an entry left without content is removed. True when
    /// there was a preset.
    pub fn clear_preset(&mut self, id: u32) -> bool {
        let count = self.count;
        let at = match self.entries.iter().take(count).position(|e| e.id == id) {
            Some(at) => at,
            None => return false,
        };
        let (had, empty) = match self.entries.get_mut(at) {
            Some(entry) => {
                let had = entry.preset.is_some();
                entry.preset = None;
                (had, entry.is_empty())
            }
            None => return false,
        };
        if empty {
            if let Some(tail) = self.entries.get_mut(at..count) {
                tail.rotate_left(1);
            }
            self.count = count - 1;
        }
        had
    }
}

/// What the parser saw, for the load-time log.
pub struct Report {
    pub state: FileState,
    /// 1, 2 or 3 when the first line was accepted, else 0.
    pub version: u8,
    /// Lines in the file, the version line included.
    pub lines: u32,
    /// Lines accepted (replacements included), value, `preset` and `option` lines together.
    pub accepted: u32,
    /// Accepted `preset` lines.
    pub preset_lines: u32,
    /// Accepted `option` lines.
    pub option_lines: u32,
    /// Accepted `slot` lines.
    pub slot_lines: u32,
    /// Accepted lines that replaced an earlier one for the same id+key.
    pub replaced: u32,
    pub rejected: u32,
    /// Rejected `preset` lines that took an earlier preset of the same ID away.
    pub cleared: u32,
    rejects: [(u32, Reject); REJECT_LOG_LIMIT],
    kept: usize,
}

impl Report {
    pub const fn new() -> Self {
        Report {
            state: FileState::Ok,
            version: 0,
            lines: 0,
            accepted: 0,
            preset_lines: 0,
            option_lines: 0,
            slot_lines: 0,
            replaced: 0,
            rejected: 0,
            cleared: 0,
            rejects: [(0, Reject::NonUtf8); REJECT_LOG_LIMIT],
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

fn hex_value(b: u8) -> Option<u32> {
    match b {
        b'0'..=b'9' => Some((b - b'0') as u32),
        b'a'..=b'f' => Some((b - b'a') as u32 + 10),
        b'A'..=b'F' => Some((b - b'A') as u32 + 10),
        _ => None,
    }
}

/// Exactly eight hex digits. `00000000` is reported separately.
pub fn parse_id(field: &str) -> Result<u32, Reject> {
    if field.len() != 8 {
        return Err(Reject::BadId);
    }
    let mut id = 0u32;
    for &b in field.as_bytes() {
        match hex_value(b) {
            Some(nib) => id = (id << 4) | nib,
            None => return Err(Reject::BadId),
        }
    }
    if id == 0 {
        Err(Reject::ZeroId)
    } else {
        Ok(id)
    }
}

pub fn key_index(field: &str) -> Option<usize> {
    KEY_NAMES.iter().position(|name| *name == field)
}

/// Plain decimal: optional `-`, digits, optionally `.` and digits. No exponent, no
/// `inf`/`nan`, at most 18 digits, so the result is always finite.
pub fn parse_decimal_bytes(bytes: &[u8]) -> Option<f32> {
    if bytes.is_empty() || bytes.len() > VALUE_MAX_LEN {
        return None;
    }
    let (negative, digits) = match bytes.split_first() {
        Some((b'-', rest)) => (true, rest),
        _ => (false, bytes),
    };
    let mut mantissa = 0u64;
    let mut scale = 1.0f64;
    let mut int_digits = 0u32;
    let mut frac_digits = 0u32;
    let mut seen_point = false;
    for &b in digits {
        match b {
            b'0'..=b'9' => {
                if int_digits + frac_digits >= VALUE_MAX_DIGITS {
                    return None;
                }
                mantissa = mantissa * 10 + (b - b'0') as u64;
                if seen_point {
                    frac_digits += 1;
                    scale *= 10.0;
                } else {
                    int_digits += 1;
                }
            }
            b'.' if !seen_point => seen_point = true,
            _ => return None,
        }
    }
    if int_digits == 0 || (seen_point && frac_digits == 0) {
        return None;
    }
    let value = (mantissa as f64 / scale) as f32;
    if !value.is_finite() {
        return None;
    }
    Some(if negative { -value } else { value })
}

pub fn parse_decimal(field: &str) -> Option<f32> {
    parse_decimal_bytes(field.as_bytes())
}

pub fn in_range(key: usize, value: f32) -> bool {
    match RANGES.get(key) {
        Some(&(low, high)) => value.is_finite() && value >= low && value <= high,
        None => false,
    }
}

fn strip_cr(line: &[u8]) -> &[u8] {
    match line.split_last() {
        Some((b'\r', rest)) => rest,
        _ => line,
    }
}

enum Fields<'a> {
    Three(&'a str, &'a str, &'a str),
    Four(&'a str, &'a str, &'a str, &'a str),
}

/// The three or four fields of a line. `Ok(None)` for a blank or comment-only line.
fn split_line(line: &[u8]) -> Result<Option<Fields<'_>>, Reject> {
    let text = match core::str::from_utf8(line) {
        Ok(text) => text,
        Err(_) => return Err(Reject::NonUtf8),
    };
    let text = text.split('#').next().unwrap_or("");
    let mut fields = text.split(|c| c == ' ' || c == '\t').filter(|f| !f.is_empty());
    let f1 = match fields.next() {
        Some(f) => f,
        None => return Ok(None),
    };
    let f2 = match fields.next() {
        Some(f) => f,
        None => return Err(Reject::FieldCount),
    };
    let f3 = match fields.next() {
        Some(f) => f,
        None => return Err(Reject::FieldCount),
    };
    match fields.next() {
        None => Ok(Some(Fields::Three(f1, f2, f3))),
        Some(f4) => match fields.next() {
            None => Ok(Some(Fields::Four(f1, f2, f3, f4))),
            Some(_) => Err(Reject::FieldCount),
        },
    }
}

fn parse_internal(
    bytes: &[u8],
    presets: &Presets,
    validator: &dyn OptionValidator,
    accept_v3: bool,
) -> (Box<Table>, Report) {
    let mut table = Table::boxed();
    let mut report = Report::new();
    if bytes.len() > MAX_FILE {
        report.state = FileState::TooLarge;
        return (table, report);
    }
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
            report.version = if line == VERSION_LINE_1.as_bytes() {
                1
            } else if line == VERSION_LINE_2.as_bytes() {
                2
            } else if accept_v3 && line == VERSION_LINE_3.as_bytes() {
                3
            } else {
                report.state = if line.starts_with(&[0xef, 0xbb, 0xbf]) {
                    FileState::BadVersionLineBom
                } else {
                    FileState::BadVersionLine
                };
                report.lines = 1;
                return (Table::boxed(), report);
            };
            continue;
        }
        let fields = match split_line(line) {
            Ok(None) => continue,
            Ok(Some(fields)) => fields,
            Err(why) => {
                report.reject(number, why);
                continue;
            }
        };
        let stored = match fields {
            Fields::Three(id_field, key_field, value_field) => {
                let id = match parse_id(id_field) {
                    Ok(id) => id,
                    Err(why) => {
                        report.reject(number, why);
                        continue;
                    }
                };
                if report.version >= 2 && key_field == PRESET_KEY {
                    let name = value_field.as_bytes();
                    let found = if !crate::preset::valid_name(name) {
                        Err(Reject::BadName)
                    } else {
                        presets.find_name(name).ok_or(Reject::UnknownPreset)
                    };
                    match found {
                        Ok(preset) => {
                            let done = table.set_preset(id, preset);
                            if done.is_ok() {
                                report.preset_lines += 1;
                            }
                            done
                        }
                        Err(why) => {
                            report.cleared += table.clear_preset(id) as u32;
                            Err(why)
                        }
                    }
                } else {
                    match key_index(key_field) {
                        None => Err(Reject::UnknownKey),
                        Some(key) => match parse_decimal(value_field) {
                            None => Err(Reject::BadValue),
                            Some(value) if !in_range(key, value) => Err(Reject::OutOfRange),
                            Some(value) => table.set(id, key, value),
                        },
                    }
                }
            }
            Fields::Four(id_field, key_field, field3, field4) => {
                if report.version < 3 {
                    Err(Reject::FieldCount)
                } else if key_field == OPTION_KEY {
                    let id = match parse_id(id_field) {
                        Ok(id) => id,
                        Err(why) => {
                            report.reject(number, why);
                            continue;
                        }
                    };
                    match validator.validate_option(field3, field4) {
                        Ok((entry_idx, opt_idx)) => {
                            let res = table.set_option(
                                id,
                                entry_idx as usize,
                                opt_idx as usize,
                                field3.as_bytes(),
                                field4.as_bytes(),
                            );
                            if res.is_ok() {
                                report.option_lines += 1;
                            }
                            res
                        }
                        Err(why) => {
                            report.reject(number, why);
                            continue;
                        }
                    }
                } else if key_field == SLOT_KEY {
                    let id = match parse_id(id_field) {
                        Ok(id) => id,
                        Err(why) => {
                            report.reject(number, why);
                            continue;
                        }
                    };
                    match validator.validate_slot(field3, field4, presets) {
                        Ok((entry_idx, preset_idx)) => {
                            let res = table.set_slot(
                                id,
                                entry_idx as usize,
                                preset_idx,
                                field3.as_bytes(),
                                field4.as_bytes(),
                            );
                            if res.is_ok() {
                                report.slot_lines += 1;
                            }
                            res
                        }
                        Err(why) => {
                            report.reject(number, why);
                            continue;
                        }
                    }
                } else {
                    Err(Reject::FieldCount)
                }
            }
        };
        match stored {
            Ok(replaced) => {
                report.accepted += 1;
                report.replaced += replaced as u32;
            }
            Err(why) => report.reject(number, why),
        }
    }
    report.lines = number;
    (table, report)
}

/// Parse a whole file with a validator for option entries. Lines end with `\n` or `\r\n`.
/// On any state other than [`FileState::Ok`] the returned table is empty.
pub fn parse_with_validator(
    bytes: &[u8],
    presets: &Presets,
    validator: &dyn OptionValidator,
) -> (Box<Table>, Report) {
    parse_internal(bytes, presets, validator, true)
}

/// Parse a whole file without option entries (for 0.6.0 backwards compatibility).
pub fn parse(bytes: &[u8], presets: &Presets) -> (Box<Table>, Report) {
    parse_internal(bytes, presets, &NoOptions, false)
}

// ---------------------------------------------------------------------------
// Which file is the loadout file (contract B+)
// ---------------------------------------------------------------------------

/// What reading one of the two files gave.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Probe<'a> {
    /// The file does not exist.
    Absent,
    /// It exists (or may exist) and could not be read.
    Unreadable,
    Bytes(&'a [u8]),
}

/// Where the published table came from.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Origin {
    /// `loadouts.txt` was read (well-formed or not).
    Main,
    /// `loadouts.txt` does not exist and `loadouts.new` is a well-formed file: the window
    /// between "old file deleted" and "new file renamed" of an interrupted save.
    Recovered,
    /// No usable file.
    Off,
}

impl Origin {
    pub fn name(self) -> &'static str {
        match self {
            Origin::Main => "main",
            Origin::Recovered => "recovered_new",
            Origin::Off => "off",
        }
    }
}

/// Contract B+: `loadouts.txt` when it exists, whatever it holds; `loadouts.new` only when
/// `loadouts.txt` does not exist and `loadouts.new` parses as a whole (state `Ok`).
pub fn load_with_validator(
    main: Probe,
    new: Probe,
    presets: &Presets,
    validator: &dyn OptionValidator,
) -> (Box<Table>, Report, Origin) {
    match main {
        Probe::Bytes(bytes) => {
            let (table, report) = parse_with_validator(bytes, presets, validator);
            (table, report, Origin::Main)
        }
        Probe::Unreadable => (Table::boxed(), Report::new(), Origin::Off),
        Probe::Absent => match new {
            Probe::Bytes(bytes) => {
                let (table, report) = parse_with_validator(bytes, presets, validator);
                if report.state == FileState::Ok {
                    (table, report, Origin::Recovered)
                } else {
                    (Table::boxed(), report, Origin::Off)
                }
            }
            _ => (Table::boxed(), Report::new(), Origin::Off),
        },
    }
}

/// Contract B+ for callers without option entries.
pub fn load(main: Probe, new: Probe, presets: &Presets) -> (Box<Table>, Report, Origin) {
    load_with_validator(main, new, presets, &NoOptions)
}

// ---------------------------------------------------------------------------
// Table -> file text
// ---------------------------------------------------------------------------

/// Why [`serialise`] produced nothing usable.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum SerError {
    /// The text does not fit the buffer or the 16 KiB file limit.
    Overflow,
    /// An entry names a preset index that has no name.
    Preset,
    /// A value has no decimal form that [`parse_decimal`] reads back to the same bits.
    Number,
}

struct Writer<'a> {
    buf: &'a mut [u8],
    len: usize,
    overflow: bool,
}

impl<'a> Writer<'a> {
    fn bytes(&mut self, text: &[u8]) {
        for &b in text {
            match self.buf.get_mut(self.len) {
                Some(slot) => {
                    *slot = b;
                    self.len += 1;
                }
                None => self.overflow = true,
            }
        }
    }

    fn id(&mut self, id: u32) {
        let mut i = 8;
        while i > 0 {
            i -= 1;
            let nib = ((id >> (i * 4)) & 0xf) as u8;
            self.bytes(&[if nib < 10 { b'0' + nib } else { b'a' + (nib - 10) }]);
        }
    }
}

/// Shortest plain decimal of `value` that [`parse_decimal`] reads back to exactly the same
/// bits: no exponent, at most 18 digits. Returns the text length, `None` when there is no
/// such form (not finite, or too small / too large for 18 digits).
pub fn format_value(value: f32, out: &mut [u8; VALUE_MAX_LEN]) -> Option<usize> {
    if !value.is_finite() {
        return None;
    }
    let negative = value.is_sign_negative();
    let magnitude = (if negative { -value } else { value }) as f64;
    let mut pow = 1.0f64;
    let mut frac_digits = 0usize;
    while frac_digits <= VALUE_MAX_DIGITS as usize {
        let scaled = magnitude * pow + 0.5;
        if scaled >= 1.0e18 {
            break;
        }
        let mut digits = scaled as u64;
        // Decimal digits of `digits`, least significant first.
        let mut tmp = [b'0'; 20];
        let mut n = 0usize;
        while digits != 0 || n <= frac_digits {
            if let Some(slot) = tmp.get_mut(n) {
                *slot = b'0' + (digits % 10) as u8;
            }
            digits /= 10;
            n += 1;
            if n >= tmp.len() {
                break;
            }
        }
        let mut len = 0usize;
        let mut push = |b: u8, len: &mut usize| {
            if let Some(slot) = out.get_mut(*len) {
                *slot = b;
                *len += 1;
            }
        };
        if negative {
            push(b'-', &mut len);
        }
        let mut i = n;
        while i > 0 {
            i -= 1;
            if i + 1 == frac_digits {
                push(b'.', &mut len);
            }
            push(tmp.get(i).copied().unwrap_or(b'0'), &mut len);
        }
        if let Some(text) = out.get(..len) {
            if parse_decimal_bytes(text).map(f32::to_bits) == Some(value.to_bits()) {
                return Some(len);
            }
        }
        pow *= 10.0;
        frac_digits += 1;
    }
    None
}

/// File text (`mc_loadouts 2` or `mc_loadouts 3`) of `table`: per ID, in table order, its
/// `preset` line, its explicit lines in key order, and its `option` lines in option order.
/// Version 3 is emitted only when at least one option line exists. Returns the text length.
pub fn serialise(table: &Table, presets: &Presets, out: &mut [u8]) -> Result<usize, SerError> {
    let mut w = Writer { buf: out, len: 0, overflow: false };
    let has_any_v3 = table.entries().iter().any(|e| e.options_count > 0 || e.slots_count > 0);
    if has_any_v3 {
        w.bytes(VERSION_LINE_3.as_bytes());
    } else {
        w.bytes(VERSION_LINE_2.as_bytes());
    }
    w.bytes(b"\n");
    for entry in table.entries() {
        if let Some(preset) = entry.preset {
            let mut name = [0u8; NAME_BUF];
            let len = presets.name(preset, &mut name);
            let name = match name.get(..len) {
                Some(name) if len != 0 => name,
                _ => return Err(SerError::Preset),
            };
            w.id(entry.id);
            w.bytes(b" ");
            w.bytes(PRESET_KEY.as_bytes());
            w.bytes(b" ");
            w.bytes(name);
            w.bytes(b"\n");
        }
        for (key, key_name) in KEY_NAMES.iter().enumerate() {
            if entry.has.get(key) != Some(&true) {
                continue;
            }
            let mut text = [0u8; VALUE_MAX_LEN];
            let value = entry.value.get(key).copied().unwrap_or(f32::NAN);
            let len = format_value(value, &mut text).ok_or(SerError::Number)?;
            w.id(entry.id);
            w.bytes(b" ");
            w.bytes(key_name.as_bytes());
            w.bytes(b" ");
            w.bytes(text.get(..len).unwrap_or(&[]));
            w.bytes(b"\n");
        }
        for opt_choice in entry.options.iter().take(entry.options_count as usize) {
            if opt_choice.entry_len > 0 && opt_choice.option_len > 0 {
                w.id(entry.id);
                w.bytes(b" option ");
                w.bytes(opt_choice.entry_id());
                w.bytes(b" ");
                w.bytes(opt_choice.option_id());
                w.bytes(b"\n");
            }
        }
        for slot_choice in entry.slots.iter().take(entry.slots_count as usize) {
            if slot_choice.entry_len > 0 && slot_choice.preset_len > 0 {
                // The stored preset index names the donor; `preset_name` (from the menu's
                // `slot_names`) is only the fallback, since an entry can have several donors.
                let mut name = [0u8; NAME_BUF];
                let len = presets.name(slot_choice.preset, &mut name);
                w.id(entry.id);
                w.bytes(b" slot ");
                w.bytes(slot_choice.entry_id());
                w.bytes(b" ");
                match name.get(..len) {
                    Some(name) if len != 0 => w.bytes(name),
                    _ => w.bytes(slot_choice.preset_name()),
                }
                w.bytes(b"\n");
            }
        }
    }
    if w.overflow || w.len > MAX_FILE {
        Err(SerError::Overflow)
    } else {
        Ok(w.len)
    }
}

// ---------------------------------------------------------------------------
// The copy the hook reads
// ---------------------------------------------------------------------------

/// A value found for one request.
#[derive(Clone, Copy, PartialEq, Debug)]
pub struct Hit {
    /// Store entry index, for the once-per-(id, field) `OV` line.
    pub entry: usize,
    pub value: f32,
    pub src: Src,
}

/// The copy of the table the hook reads. Written by [`Store::publish`] at plugin load,
/// before any hook is installed, and afterwards only by [`Store::set_preset`] and
/// [`Store::set_option`] (one writer, the UI thread).
pub struct Store {
    ids: [AtomicU32; MAX_IDS],
    /// 0 = no preset, otherwise preset index + 1.
    presets: [AtomicU32; MAX_IDS],
    has: [[AtomicBool; KEYS]; MAX_IDS],
    bits: [[AtomicU32; KEYS]; MAX_IDS],
    /// Bit `f` set: the override of field index `f` was applied once; for the `OV` line.
    applied: [AtomicU64; MAX_IDS],
    options_entry: [[AtomicU8; MAX_LOADOUT_OPTIONS]; MAX_IDS],
    options_val: [[AtomicU8; MAX_LOADOUT_OPTIONS]; MAX_IDS],
    options_count: [AtomicU8; MAX_IDS],
    slots_entry: [[AtomicU8; MAX_LOADOUT_SLOTS]; MAX_IDS],
    slots_preset: [[AtomicU32; MAX_LOADOUT_SLOTS]; MAX_IDS],
    slots_count: [AtomicU8; MAX_IDS],
    count: AtomicU32,
    /// Runtime changes since load; lets the log treat a fighter as new after a change.
    generation: AtomicU32,
}

/// Result of [`Store::set_preset`] or [`Store::set_option`].
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Update {
    /// The ID already had exactly this choice.
    Unchanged,
    /// An existing entry changed.
    Changed,
    /// A new entry was appended.
    Added,
    /// All [`MAX_IDS`] entries are taken by other IDs, or options capacity full; nothing was changed.
    Full,
    /// ID 0 never has a loadout; nothing was changed.
    ZeroId,
}

impl Update {
    pub fn name(self) -> &'static str {
        match self {
            Update::Unchanged => "unchanged",
            Update::Changed => "changed",
            Update::Added => "added",
            Update::Full => "store_full",
            Update::ZeroId => "zero_id",
        }
    }
}

const U8_ZERO: AtomicU8 = AtomicU8::new(0);
const U32_ZERO: AtomicU32 = AtomicU32::new(0);
const U64_ZERO: AtomicU64 = AtomicU64::new(0);
const U32_PAIR: [AtomicU32; KEYS] = [U32_ZERO; KEYS];
const BOOL_FALSE: AtomicBool = AtomicBool::new(false);
const BOOL_PAIR: [AtomicBool; KEYS] = [BOOL_FALSE; KEYS];
const OPT_ENTRY_ARRAY: [AtomicU8; MAX_LOADOUT_OPTIONS] = [U8_ZERO; MAX_LOADOUT_OPTIONS];
const OPT_VAL_ARRAY: [AtomicU8; MAX_LOADOUT_OPTIONS] = [U8_ZERO; MAX_LOADOUT_OPTIONS];
const SLOT_ENTRY_ARRAY: [AtomicU8; MAX_LOADOUT_SLOTS] = [U8_ZERO; MAX_LOADOUT_SLOTS];
const SLOT_PRESET_ARRAY: [AtomicU32; MAX_LOADOUT_SLOTS] = [U32_ZERO; MAX_LOADOUT_SLOTS];

impl Store {
    pub const fn new() -> Self {
        Store {
            ids: [U32_ZERO; MAX_IDS],
            presets: [U32_ZERO; MAX_IDS],
            has: [BOOL_PAIR; MAX_IDS],
            bits: [U32_PAIR; MAX_IDS],
            applied: [U64_ZERO; MAX_IDS],
            options_entry: [OPT_ENTRY_ARRAY; MAX_IDS],
            options_val: [OPT_VAL_ARRAY; MAX_IDS],
            options_count: [U8_ZERO; MAX_IDS],
            slots_entry: [SLOT_ENTRY_ARRAY; MAX_IDS],
            slots_preset: [SLOT_PRESET_ARRAY; MAX_IDS],
            slots_count: [U8_ZERO; MAX_IDS],
            count: AtomicU32::new(0),
            generation: AtomicU32::new(0),
        }
    }

    /// Runtime writer (editor UI, one thread): give saved fighter `id` the preset with
    /// index `preset`, or take its preset away (`None`). Explicit values of the ID stay.
    pub fn set_preset(&self, id: u32, preset: Option<usize>) -> Update {
        if id == 0 {
            return Update::ZeroId;
        }
        let word = match preset {
            Some(preset) if preset < u32::MAX as usize => preset as u32 + 1,
            Some(_) => return Update::Unchanged,
            None => 0,
        };
        let len = self.len();
        let found = self.ids.iter().take(len).position(|slot| slot.load(Ordering::Relaxed) == id);
        if let Some(entry) = found {
            let (cell, applied) = match (self.presets.get(entry), self.applied.get(entry)) {
                (Some(cell), Some(applied)) => (cell, applied),
                _ => return Update::Unchanged,
            };
            if cell.load(Ordering::Relaxed) == word {
                return Update::Unchanged;
            }
            cell.store(word, Ordering::Release);
            applied.store(0, Ordering::Relaxed);
            self.generation.fetch_add(1, Ordering::Relaxed);
            return Update::Changed;
        }
        if word == 0 {
            return Update::Unchanged;
        }
        let (slot, cell, has, bits, applied, opt_count, slot_count) =
            match (self.ids.get(len), self.presets.get(len), self.has.get(len), self.bits.get(len), self.applied.get(len), self.options_count.get(len), self.slots_count.get(len)) {
                (Some(slot), Some(cell), Some(has), Some(bits), Some(applied), Some(opt_count), Some(slot_count)) => (slot, cell, has, bits, applied, opt_count, slot_count),
                _ => return Update::Full,
            };
        for (h, b) in has.iter().zip(bits.iter()) {
            h.store(false, Ordering::Relaxed);
            b.store(0, Ordering::Relaxed);
        }
        applied.store(0, Ordering::Relaxed);
        opt_count.store(0, Ordering::Relaxed);
        slot_count.store(0, Ordering::Relaxed);
        cell.store(word, Ordering::Relaxed);
        slot.store(id, Ordering::Relaxed);
        self.count.store(len as u32 + 1, Ordering::Release);
        self.generation.fetch_add(1, Ordering::Relaxed);
        Update::Added
    }

    /// Option index of saved fighter `id` for menu entry `entry_idx`, `None` for default (0).
    pub fn option_of_id(&self, id: u32, entry_idx: usize) -> Option<usize> {
        if id == 0 {
            return None;
        }
        let entry = self.ids.iter().take(self.len()).position(|slot| slot.load(Ordering::Relaxed) == id)?;
        let count = self.options_count.get(entry)?.load(Ordering::Relaxed) as usize;
        let entries = self.options_entry.get(entry)?;
        let vals = self.options_val.get(entry)?;
        for i in 0..count {
            if entries[i].load(Ordering::Relaxed) as usize == entry_idx {
                return Some(vals[i].load(Ordering::Relaxed) as usize);
            }
        }
        None
    }

    /// Runtime writer (editor UI, one thread): set option choice for entry `entry_idx`.
    /// `option_idx == 0` removes the choice.
    pub fn set_option(&self, id: u32, entry_idx: usize, option_idx: usize) -> Update {
        if id == 0 {
            return Update::ZeroId;
        }
        let len = self.len();
        let found = self.ids.iter().take(len).position(|slot| slot.load(Ordering::Relaxed) == id);
        if let Some(entry) = found {
            let count_cell = match self.options_count.get(entry) {
                Some(c) => c,
                None => return Update::Unchanged,
            };
            let count = count_cell.load(Ordering::Relaxed) as usize;
            let entries = match self.options_entry.get(entry) {
                Some(e) => e,
                None => return Update::Unchanged,
            };
            let vals = match self.options_val.get(entry) {
                Some(v) => v,
                None => return Update::Unchanged,
            };
            let mut existing = None;
            for i in 0..count {
                if entries[i].load(Ordering::Relaxed) as usize == entry_idx {
                    existing = Some(i);
                    break;
                }
            }
            if option_idx == 0 {
                if let Some(pos) = existing {
                    for i in pos..count.saturating_sub(1) {
                        entries[i].store(entries[i + 1].load(Ordering::Relaxed), Ordering::Relaxed);
                        vals[i].store(vals[i + 1].load(Ordering::Relaxed), Ordering::Relaxed);
                    }
                    count_cell.store((count - 1) as u8, Ordering::Release);
                    self.generation.fetch_add(1, Ordering::Relaxed);
                    return Update::Changed;
                } else {
                    return Update::Unchanged;
                }
            } else {
                if let Some(pos) = existing {
                    if vals[pos].load(Ordering::Relaxed) as usize == option_idx {
                        return Update::Unchanged;
                    }
                    vals[pos].store(option_idx as u8, Ordering::Release);
                    self.generation.fetch_add(1, Ordering::Relaxed);
                    return Update::Changed;
                }
                if count >= MAX_LOADOUT_OPTIONS {
                    return Update::Full;
                }
                entries[count].store(entry_idx as u8, Ordering::Relaxed);
                vals[count].store(option_idx as u8, Ordering::Relaxed);
                count_cell.store((count + 1) as u8, Ordering::Release);
                self.generation.fetch_add(1, Ordering::Relaxed);
                return Update::Changed;
            }
        }
        if option_idx == 0 {
            return Update::Unchanged;
        }
        if len >= MAX_IDS {
            return Update::Full;
        }
        let (slot, cell, has, bits, applied, opt_count, slot_count, entries, vals) =
            match (self.ids.get(len), self.presets.get(len), self.has.get(len), self.bits.get(len), self.applied.get(len), self.options_count.get(len), self.slots_count.get(len), self.options_entry.get(len), self.options_val.get(len)) {
                (Some(slot), Some(cell), Some(has), Some(bits), Some(applied), Some(opt_count), Some(slot_count), Some(entries), Some(vals)) => (slot, cell, has, bits, applied, opt_count, slot_count, entries, vals),
                _ => return Update::Full,
            };
        cell.store(0, Ordering::Relaxed);
        for (h, b) in has.iter().zip(bits.iter()) {
            h.store(false, Ordering::Relaxed);
            b.store(0, Ordering::Relaxed);
        }
        applied.store(0, Ordering::Relaxed);
        slot_count.store(0, Ordering::Relaxed);
        entries[0].store(entry_idx as u8, Ordering::Relaxed);
        vals[0].store(option_idx as u8, Ordering::Relaxed);
        opt_count.store(1, Ordering::Relaxed);
        slot.store(id, Ordering::Relaxed);
        self.count.store(len as u32 + 1, Ordering::Release);
        self.generation.fetch_add(1, Ordering::Relaxed);
        Update::Added
    }

    /// Slot preset index of saved fighter `id` for menu entry `entry_idx`, `None` for default (0).
    pub fn slot_of_id(&self, id: u32, entry_idx: usize) -> Option<usize> {
        if id == 0 {
            return None;
        }
        let entry = self.ids.iter().take(self.len()).position(|slot| slot.load(Ordering::Relaxed) == id)?;
        let count = self.slots_count.get(entry)?.load(Ordering::Relaxed) as usize;
        let entries = self.slots_entry.get(entry)?;
        let presets = self.slots_preset.get(entry)?;
        for i in 0..count {
            if entries[i].load(Ordering::Relaxed) as usize == entry_idx {
                return Some(presets[i].load(Ordering::Relaxed) as usize);
            }
        }
        None
    }

    /// Runtime writer (editor UI, one thread): set slot choice for entry `entry_idx`.
    /// `preset == None` removes the choice.
    pub fn set_slot(&self, id: u32, entry_idx: usize, preset: Option<usize>) -> Update {
        if id == 0 {
            return Update::ZeroId;
        }
        let len = self.len();
        let found = self.ids.iter().take(len).position(|slot| slot.load(Ordering::Relaxed) == id);
        if let Some(entry) = found {
            let count_cell = match self.slots_count.get(entry) {
                Some(c) => c,
                None => return Update::Unchanged,
            };
            let count = count_cell.load(Ordering::Relaxed) as usize;
            let entries = match self.slots_entry.get(entry) {
                Some(e) => e,
                None => return Update::Unchanged,
            };
            let presets = match self.slots_preset.get(entry) {
                Some(v) => v,
                None => return Update::Unchanged,
            };
            let mut existing = None;
            for i in 0..count {
                if entries[i].load(Ordering::Relaxed) as usize == entry_idx {
                    existing = Some(i);
                    break;
                }
            }
            if let Some(preset_val) = preset {
                if let Some(pos) = existing {
                    if presets[pos].load(Ordering::Relaxed) as usize == preset_val {
                        return Update::Unchanged;
                    }
                    presets[pos].store(preset_val as u32, Ordering::Release);
                    self.generation.fetch_add(1, Ordering::Relaxed);
                    return Update::Changed;
                }
                if count >= MAX_LOADOUT_SLOTS {
                    return Update::Full;
                }
                entries[count].store(entry_idx as u8, Ordering::Relaxed);
                presets[count].store(preset_val as u32, Ordering::Relaxed);
                count_cell.store((count + 1) as u8, Ordering::Release);
                self.generation.fetch_add(1, Ordering::Relaxed);
                return Update::Changed;
            } else {
                if let Some(pos) = existing {
                    for i in pos..count.saturating_sub(1) {
                        entries[i].store(entries[i + 1].load(Ordering::Relaxed), Ordering::Relaxed);
                        presets[i].store(presets[i + 1].load(Ordering::Relaxed), Ordering::Relaxed);
                    }
                    count_cell.store((count - 1) as u8, Ordering::Release);
                    self.generation.fetch_add(1, Ordering::Relaxed);
                    return Update::Changed;
                } else {
                    return Update::Unchanged;
                }
            }
        }
        if preset.is_none() {
            return Update::Unchanged;
        }
        let preset_val = preset.unwrap();
        if len >= MAX_IDS {
            return Update::Full;
        }
        let (slot, cell, has, bits, applied, opt_count, count_cell, sl_entries, sl_presets) =
            match (self.ids.get(len), self.presets.get(len), self.has.get(len), self.bits.get(len), self.applied.get(len), self.options_count.get(len), self.slots_count.get(len), self.slots_entry.get(len), self.slots_preset.get(len)) {
                (Some(slot), Some(cell), Some(has), Some(bits), Some(applied), Some(opt_count), Some(count_cell), Some(sl_entries), Some(sl_presets)) => (slot, cell, has, bits, applied, opt_count, count_cell, sl_entries, sl_presets),
                _ => return Update::Full,
            };
        cell.store(0, Ordering::Relaxed);
        for (h, b) in has.iter().zip(bits.iter()) {
            h.store(false, Ordering::Relaxed);
            b.store(0, Ordering::Relaxed);
        }
        applied.store(0, Ordering::Relaxed);
        opt_count.store(0, Ordering::Relaxed);
        sl_entries[0].store(entry_idx as u8, Ordering::Relaxed);
        sl_presets[0].store(preset_val as u32, Ordering::Relaxed);
        count_cell.store(1, Ordering::Relaxed);
        slot.store(id, Ordering::Relaxed);
        self.count.store(len as u32 + 1, Ordering::Release);
        self.generation.fetch_add(1, Ordering::Relaxed);
        Update::Added
    }

    /// Preset index of saved fighter `id`, `None` when it has no entry or no preset.
    pub fn preset_of_id(&self, id: u32) -> Option<usize> {
        if id == 0 {
            return None;
        }
        let entry = self.ids.iter().take(self.len()).position(|slot| slot.load(Ordering::Relaxed) == id)?;
        self.preset_of(entry)
    }

    /// Number of runtime changes since load.
    pub fn generation(&self) -> u32 {
        self.generation.load(Ordering::Relaxed)
    }

    pub fn publish(&self, table: &Table) {
        self.count.store(0, Ordering::Release);
        let mut stored = 0u32;
        for (i, entry) in table.entries().iter().enumerate() {
            let (id, preset, has, bits, applied, opt_count, entries, vals, slot_count, sl_entries, sl_presets) =
                match (self.ids.get(i), self.presets.get(i), self.has.get(i), self.bits.get(i), self.applied.get(i), self.options_count.get(i), self.options_entry.get(i), self.options_val.get(i), self.slots_count.get(i), self.slots_entry.get(i), self.slots_preset.get(i)) {
                    (Some(id), Some(preset), Some(has), Some(bits), Some(applied), Some(opt_count), Some(entries), Some(vals), Some(slot_count), Some(sl_entries), Some(sl_presets)) => (id, preset, has, bits, applied, opt_count, entries, vals, slot_count, sl_entries, sl_presets),
                    _ => break,
                };
            id.store(entry.id, Ordering::Relaxed);
            preset.store(entry.preset.map(|p| p as u32 + 1).unwrap_or(0), Ordering::Relaxed);
            applied.store(0, Ordering::Relaxed);
            for key in 0..KEYS {
                if let (Some(h), Some(b), Some(eh), Some(ev)) =
                    (has.get(key), bits.get(key), entry.has.get(key), entry.value.get(key))
                {
                    b.store(ev.to_bits(), Ordering::Relaxed);
                    h.store(*eh, Ordering::Relaxed);
                }
            }
            let count = entry.options_count.min(MAX_LOADOUT_OPTIONS as u8);
            opt_count.store(count, Ordering::Relaxed);
            for j in 0..count as usize {
                entries[j].store(entry.options[j].entry, Ordering::Relaxed);
                vals[j].store(entry.options[j].option, Ordering::Relaxed);
            }
            let scount = entry.slots_count.min(MAX_LOADOUT_SLOTS as u8);
            slot_count.store(scount, Ordering::Relaxed);
            for j in 0..scount as usize {
                sl_entries[j].store(entry.slots[j].entry, Ordering::Relaxed);
                sl_presets[j].store(entry.slots[j].preset as u32, Ordering::Relaxed);
            }
            stored += 1;
        }
        self.count.store(stored, Ordering::Release);
    }

    /// The store's content as a table, in store order.
    pub fn snapshot(&self) -> Box<Table> {
        self.snapshot_with_validator(&NoOptions)
    }

    pub fn snapshot_with_validator(&self, validator: &dyn OptionValidator) -> Box<Table> {
        let mut table = Table::boxed();
        for i in 0..self.len() {
            let (id, preset, has, bits) = match (self.ids.get(i), self.presets.get(i), self.has.get(i), self.bits.get(i)) {
                (Some(id), Some(preset), Some(has), Some(bits)) => (id, preset, has, bits),
                _ => break,
            };
            let id = id.load(Ordering::Relaxed);
            let preset = preset.load(Ordering::Relaxed);
            if preset != 0 {
                let _ = table.set_preset(id, preset as usize - 1);
            }
            for key in 0..KEYS {
                if let (Some(h), Some(b)) = (has.get(key), bits.get(key)) {
                    if h.load(Ordering::Relaxed) {
                        let _ = table.set(id, key, f32::from_bits(b.load(Ordering::Relaxed)));
                    }
                }
            }
            let opt_count = self.options_count.get(i).map(|c| c.load(Ordering::Relaxed) as usize).unwrap_or(0);
            if let (Some(entries), Some(vals)) = (self.options_entry.get(i), self.options_val.get(i)) {
                for j in 0..opt_count {
                    let e_idx = entries[j].load(Ordering::Relaxed) as usize;
                    let o_idx = vals[j].load(Ordering::Relaxed) as usize;
                    let (eid, oid) = validator.option_names(e_idx as u8, o_idx as u8).unwrap_or((&[], &[]));
                    let _ = table.set_option(id, e_idx, o_idx, eid, oid);
                }
            }
            let scount = self.slots_count.get(i).map(|c| c.load(Ordering::Relaxed) as usize).unwrap_or(0);
            if let (Some(entries), Some(presets)) = (self.slots_entry.get(i), self.slots_preset.get(i)) {
                for j in 0..scount {
                    let e_idx = entries[j].load(Ordering::Relaxed) as usize;
                    let p_idx = presets[j].load(Ordering::Relaxed) as usize;
                    let (eid, pname) = validator.slot_names(e_idx as u8, p_idx).unwrap_or((&[], &[]));
                    let _ = table.set_slot(id, e_idx, p_idx, eid, pname);
                }
            }
        }
        table
    }

    pub fn len(&self) -> usize {
        (self.count.load(Ordering::Acquire) as usize).min(MAX_IDS)
    }

    /// Contract B's resolution for field index `field` of saved fighter `id`: an explicit
    /// value (inside its accepted range) wins; otherwise the value of the ID's preset, if
    /// it has one and the preset has the field; otherwise `None` (the game's value).
    pub fn resolve(&self, id: u32, field: usize, presets: &Presets) -> Option<Hit> {
        if id == 0 {
            return None;
        }
        let entry = self
            .ids
            .iter()
            .take(self.len())
            .position(|slot| slot.load(Ordering::Relaxed) == id)?;
        if field < KEYS && self.has.get(entry)?.get(field)?.load(Ordering::Relaxed) {
            let value = f32::from_bits(self.bits.get(entry)?.get(field)?.load(Ordering::Relaxed));
            if in_range(field, value) {
                return Some(Hit { entry, value, src: Src::Explicit });
            }
        }
        let preset = self.presets.get(entry)?.load(Ordering::Relaxed);
        if preset == 0 {
            return None;
        }
        let value = presets.value(preset as usize - 1, field)?;
        Some(Hit { entry, value, src: Src::Preset })
    }

    /// Preset index of store entry `entry`, `None` when it has no preset.
    pub fn preset_of(&self, entry: usize) -> Option<usize> {
        if entry >= self.len() {
            return None;
        }
        match self.presets.get(entry)?.load(Ordering::Relaxed) {
            0 => None,
            preset => Some(preset as usize - 1),
        }
    }

    /// True exactly once per (entry, field index).
    pub fn first_apply(&self, entry: usize, field: usize) -> bool {
        if field >= 64 {
            return false;
        }
        match self.applied.get(entry) {
            Some(mask) => mask.fetch_or(1u64 << field, Ordering::Relaxed) & (1u64 << field) == 0,
            None => false,
        }
    }
}
