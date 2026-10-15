//! Preset file, format `mc_presets 1` (contract A of `prompts/P7-PRESET-ENGINE.md`), and
//! the table of field hashes the hook reacts to.
//!
//! ```text
//! mc_presets 1
//! # comment
//! fighter <name: [a-z0-9_]{1,31}> <kind hash: 0x + 10 hex digits>
//! <field hash: 0x + 10 hex digits> <decimal value>
//! ```
//!
//! Pure: no skyline items, no heap, no locks, no panicking paths. [`Presets`] is fixed-size
//! and made of atomics only, so the parser fills it through `&self` and the hook reads it
//! without `unsafe`. It is written once, at plugin load, before any hook exists, and only
//! read afterwards. Compiled unchanged into the host test
//! (`scratch/2026-10-05_P7-PRESET-ENGINE/host_test.rs`).

use crate::loadout::parse_decimal_bytes;
use core::sync::atomic::{AtomicU32, AtomicU64, AtomicU8, Ordering};

pub const VERSION_LINE: &str = "mc_presets 1";
/// Largest accepted file. A longer file gives no presets at all.
pub const MAX_FILE: usize = 512 * 1024;
pub const MAX_PRESETS: usize = 128;
/// Fields accepted per preset. A repeated field inside one preset is rejected before this
/// is asked, so the limit is reached by a preset that holds 48 different fields.
pub const MAX_PRESET_FIELDS: usize = 48;
/// Distinct field hashes accepted over the whole file.
pub const MAX_FILE_HASHES: usize = 48;
pub const NAME_MAX: usize = 31;
/// Name buffer: [`NAME_MAX`] bytes and at least one NUL.
pub const NAME_BUF: usize = NAME_MAX + 1;
/// Rejected lines remembered for the log; further ones are only counted.
pub const REJECT_LOG_LIMIT: usize = 32;

/// The two fields a loadout file can set by name. Their field indexes are 0 and 1 whether
/// or not a preset file exists.
pub const HASH_WEIGHT: u64 = 0x06_07cd_5541;
pub const HASH_WALK_SPEED_MAX: u64 = 0x0e_e2ec_2860;
pub const NAMED: usize = 2;
pub const NAMED_HASHES: [u64; NAMED] = [HASH_WEIGHT, HASH_WALK_SPEED_MAX];
/// Every hash the hook can know: the named two plus the file's.
pub const FIELDS: usize = MAX_FILE_HASHES + NAMED;
/// Slots of the open-addressing table; a power of two, at least five times [`FIELDS`].
pub const HASH_SLOTS: usize = 256;

const U8_ZERO: AtomicU8 = AtomicU8::new(0);
const U32_ZERO: AtomicU32 = AtomicU32::new(0);
const U64_ZERO: AtomicU64 = AtomicU64::new(0);

/// Home slot of a hash: the top eight bits of a multiplicative mix.
#[inline(always)]
pub fn home_slot(hash: u64) -> usize {
    ((hash ^ (hash >> 32)).wrapping_mul(0x9e37_79b9_7f4a_7c15) >> 56) as usize
}

/// Field hash -> field index, built at load. Linear probing, no deletion. Key 0 is "empty",
/// so hash 0 is never stored and never found.
pub struct FieldTable {
    keys: [AtomicU64; HASH_SLOTS],
    index: [AtomicU8; HASH_SLOTS],
    /// Hash of each field index.
    hashes: [AtomicU64; FIELDS],
    count: AtomicU32,
    /// Slots a lookup may have to examine: the longest probe sequence of any stored key.
    probe_max: AtomicU32,
}

impl FieldTable {
    pub const fn new() -> Self {
        FieldTable {
            keys: [U64_ZERO; HASH_SLOTS],
            index: [U8_ZERO; HASH_SLOTS],
            hashes: [U64_ZERO; FIELDS],
            count: AtomicU32::new(0),
            probe_max: AtomicU32::new(0),
        }
    }

    /// Field index of `hash`, `None` when the hash is not in the table.
    ///
    /// This is the hook's test for every request. Cost of a miss: one load of the probe
    /// bound, the mix (one multiply), then per examined slot one load and two compares;
    /// it stops at the first empty slot and never examines more than `probe_max` slots
    /// (at most [`FIELDS`]). No call, no lock, no write.
    #[inline(always)]
    pub fn find(&self, hash: u64) -> Option<usize> {
        let mut left = self.probe_max.load(Ordering::Relaxed);
        let mut slot = home_slot(hash);
        while left != 0 {
            let key = match self.keys.get(slot) {
                Some(cell) => cell.load(Ordering::Relaxed),
                None => return None,
            };
            if key == 0 {
                return None;
            }
            if key == hash {
                return self.index.get(slot).map(|cell| cell.load(Ordering::Relaxed) as usize);
            }
            slot = (slot + 1) & (HASH_SLOTS - 1);
            left -= 1;
        }
        None
    }

    /// Add `hash` (load time only, one thread). Returns its field index; `None` for hash 0
    /// or a full table.
    pub fn insert(&self, hash: u64) -> Option<usize> {
        if hash == 0 {
            return None;
        }
        if let Some(found) = self.find(hash) {
            return Some(found);
        }
        let field = self.count.load(Ordering::Relaxed) as usize;
        if field >= FIELDS {
            return None;
        }
        let mut slot = home_slot(hash);
        let mut examined = 1u32;
        while examined as usize <= HASH_SLOTS {
            let (key, index) = match (self.keys.get(slot), self.index.get(slot)) {
                (Some(key), Some(index)) => (key, index),
                _ => return None,
            };
            if key.load(Ordering::Relaxed) == 0 {
                // Index and bound first: a concurrent reader must never find the key
                // before they are valid.
                index.store(field as u8, Ordering::Relaxed);
                if let Some(cell) = self.hashes.get(field) {
                    cell.store(hash, Ordering::Relaxed);
                }
                key.store(hash, Ordering::Release);
                if examined > self.probe_max.load(Ordering::Relaxed) {
                    self.probe_max.store(examined, Ordering::Release);
                }
                self.count.store(field as u32 + 1, Ordering::Release);
                return Some(field);
            }
            slot = (slot + 1) & (HASH_SLOTS - 1);
            examined += 1;
        }
        None
    }

    pub fn len(&self) -> usize {
        (self.count.load(Ordering::Acquire) as usize).min(FIELDS)
    }

    pub fn probe_max(&self) -> u32 {
        self.probe_max.load(Ordering::Relaxed)
    }

    /// Hash of field `field`, 0 when there is no such field.
    pub fn hash_of(&self, field: usize) -> u64 {
        if field >= self.len() {
            return 0;
        }
        self.hashes.get(field).map(|cell| cell.load(Ordering::Relaxed)).unwrap_or(0)
    }
}

/// Why one line was ignored.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Reject {
    /// Not `fighter <name> <hash>` and not `<hash> <value>`.
    FieldCount,
    BadName,
    /// Not `0x` + 10 hex digits, or a field hash of zero.
    BadHash,
    /// A `fighter` line whose name already exists; the whole preset is skipped.
    DupName,
    TooManyPresets,
    /// A field line before any `fighter` line.
    NoPreset,
    /// The preset already has this field; the first value stays.
    DupField,
    TooManyFields,
    /// A 49th distinct field hash.
    TooManyHashes,
    BadValue,
}

impl Reject {
    pub fn name(self) -> &'static str {
        match self {
            Reject::FieldCount => "field_count",
            Reject::BadName => "bad_name",
            Reject::BadHash => "bad_hash",
            Reject::DupName => "dup_name",
            Reject::TooManyPresets => "too_many_presets",
            Reject::NoPreset => "no_preset",
            Reject::DupField => "dup_field",
            Reject::TooManyFields => "too_many_fields",
            Reject::TooManyHashes => "too_many_hashes",
            Reject::BadValue => "bad_value",
        }
    }
}

/// Result for the file as a whole. Everything except `Ok` means "no presets".
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum FileState {
    Ok,
    TooLarge,
    /// The first line is not exactly `mc_presets 1`.
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

/// What the parser saw, for the load-time log.
pub struct Report {
    pub state: FileState,
    /// Lines in the file, the version line included.
    pub lines: u32,
    /// Presets stored.
    pub presets: u32,
    /// Field lines stored.
    pub fields: u32,
    pub rejected: u32,
    /// Field lines that belong to a rejected `fighter` line. Not in the reject list: the
    /// `fighter` line is.
    pub skipped: u32,
    rejects: [(u32, Reject); REJECT_LOG_LIMIT],
    kept: usize,
}

impl Report {
    pub const fn new() -> Self {
        Report {
            state: FileState::Ok,
            lines: 0,
            presets: 0,
            fields: 0,
            rejected: 0,
            skipped: 0,
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

/// The presets and the field table. One static in the plugin.
pub struct Presets {
    pub fields: FieldTable,
    /// NUL-padded names.
    names: [[AtomicU8; NAME_BUF]; MAX_PRESETS],
    kinds: [AtomicU64; MAX_PRESETS],
    /// Bit `f` set: the preset has a value for field index `f`.
    masks: [AtomicU64; MAX_PRESETS],
    bits: [[AtomicU32; FIELDS]; MAX_PRESETS],
    count: AtomicU32,
    /// Bit `f` set: field index `f` occurs in the file.
    file_fields: AtomicU64,
}

const NAME_ZERO: [AtomicU8; NAME_BUF] = [U8_ZERO; NAME_BUF];
const ROW_ZERO: [AtomicU32; FIELDS] = [U32_ZERO; FIELDS];

impl Presets {
    pub const fn new() -> Self {
        Presets {
            fields: FieldTable::new(),
            names: [NAME_ZERO; MAX_PRESETS],
            kinds: [U64_ZERO; MAX_PRESETS],
            masks: [U64_ZERO; MAX_PRESETS],
            bits: [ROW_ZERO; MAX_PRESETS],
            count: AtomicU32::new(0),
            file_fields: AtomicU64::new(0),
        }
    }

    /// Give the two named keys their field indexes 0 and 1. Called once at load, before
    /// the preset file is parsed. Without it nothing is ever overridden.
    pub fn init_named(&self) {
        for hash in NAMED_HASHES.iter() {
            self.fields.insert(*hash);
        }
    }

    pub fn len(&self) -> usize {
        (self.count.load(Ordering::Acquire) as usize).min(MAX_PRESETS)
    }

    /// Distinct field hashes that occur in the file.
    pub fn file_hashes(&self) -> u32 {
        self.file_fields.load(Ordering::Relaxed).count_ones()
    }

    /// Copy the name of preset `preset` into `out`; returns its length (0 = no such preset).
    pub fn name(&self, preset: usize, out: &mut [u8; NAME_BUF]) -> usize {
        let mut len = 0;
        if preset < self.len() {
            if let Some(name) = self.names.get(preset) {
                for (cell, slot) in name.iter().zip(out.iter_mut()) {
                    let b = cell.load(Ordering::Relaxed);
                    if b == 0 || len >= NAME_MAX {
                        break;
                    }
                    *slot = b;
                    len += 1;
                }
            }
        }
        len
    }

    /// Index of the preset called `name`.
    pub fn find_name(&self, name: &[u8]) -> Option<usize> {
        if !valid_name(name) {
            return None;
        }
        let mut buf = [0u8; NAME_BUF];
        let mut preset = 0;
        while preset < self.len() {
            let len = self.name(preset, &mut buf);
            if buf.get(..len) == Some(name) {
                return Some(preset);
            }
            preset += 1;
        }
        None
    }

    /// Kind hash of the `fighter` line, 0 when there is no such preset. Not used by
    /// 0.3.0; it is what the editor UI will use to find a fighter's display name.
    #[allow(dead_code)]
    pub fn kind(&self, preset: usize) -> u64 {
        if preset >= self.len() {
            return 0;
        }
        self.kinds.get(preset).map(|cell| cell.load(Ordering::Relaxed)).unwrap_or(0)
    }

    /// Fields preset `preset` has a value for.
    pub fn field_count(&self, preset: usize) -> u32 {
        if preset >= self.len() {
            return 0;
        }
        self.masks.get(preset).map(|cell| cell.load(Ordering::Relaxed).count_ones()).unwrap_or(0)
    }

    /// The preset's value for field index `field`. `None` when the preset or the field
    /// does not exist, the preset has no such field, or the stored bits are not finite.
    pub fn value(&self, preset: usize, field: usize) -> Option<f32> {
        if preset >= self.len() || field >= FIELDS {
            return None;
        }
        if self.masks.get(preset)?.load(Ordering::Relaxed) & (1u64 << field) == 0 {
            return None;
        }
        let value = f32::from_bits(self.bits.get(preset)?.get(field)?.load(Ordering::Relaxed));
        if value.is_finite() {
            Some(value)
        } else {
            None
        }
    }

    fn begin(&self, name: &[u8], kind: u64) -> Result<usize, Reject> {
        if self.find_name(name).is_some() {
            return Err(Reject::DupName);
        }
        let preset = self.len();
        let (cells, kinds, mask) = match (self.names.get(preset), self.kinds.get(preset), self.masks.get(preset)) {
            (Some(cells), Some(kinds), Some(mask)) => (cells, kinds, mask),
            _ => return Err(Reject::TooManyPresets),
        };
        for (i, cell) in cells.iter().enumerate() {
            cell.store(name.get(i).copied().unwrap_or(0), Ordering::Relaxed);
        }
        kinds.store(kind, Ordering::Relaxed);
        mask.store(0, Ordering::Relaxed);
        self.count.store(preset as u32 + 1, Ordering::Release);
        Ok(preset)
    }

    fn set_field(&self, preset: usize, hash: u64, value: f32) -> Result<(), Reject> {
        let mask = match self.masks.get(preset) {
            Some(mask) => mask,
            None => return Err(Reject::TooManyPresets),
        };
        let have = mask.load(Ordering::Relaxed);
        let known = self.fields.find(hash);
        if let Some(field) = known {
            if have & (1u64 << field) != 0 {
                return Err(Reject::DupField);
            }
        }
        if have.count_ones() as usize >= MAX_PRESET_FIELDS {
            return Err(Reject::TooManyFields);
        }
        let in_file = self.file_fields.load(Ordering::Relaxed);
        let is_new_for_file = match known {
            Some(field) => in_file & (1u64 << field) == 0,
            None => true,
        };
        if is_new_for_file && in_file.count_ones() as usize >= MAX_FILE_HASHES {
            return Err(Reject::TooManyHashes);
        }
        let field = match known.or_else(|| self.fields.insert(hash)) {
            Some(field) => field,
            None => return Err(Reject::TooManyHashes),
        };
        match self.bits.get(preset).and_then(|row| row.get(field)) {
            Some(cell) => cell.store(value.to_bits(), Ordering::Relaxed),
            None => return Err(Reject::TooManyHashes),
        }
        self.file_fields.store(in_file | (1u64 << field), Ordering::Relaxed);
        mask.store(have | (1u64 << field), Ordering::Release);
        Ok(())
    }
}

/// `[a-z0-9_]{1,31}`.
pub fn valid_name(name: &[u8]) -> bool {
    !name.is_empty()
        && name.len() <= NAME_MAX
        && name.iter().all(|b| matches!(*b, b'a'..=b'z' | b'0'..=b'9' | b'_'))
}

/// `0x` + exactly ten hex digits (either case).
pub fn parse_hash(field: &[u8]) -> Option<u64> {
    let digits = match field {
        [b'0', b'x', rest @ ..] if rest.len() == 10 => rest,
        _ => return None,
    };
    let mut value = 0u64;
    for b in digits {
        let nib = match *b {
            b'0'..=b'9' => *b - b'0',
            b'a'..=b'f' => *b - b'a' + 10,
            b'A'..=b'F' => *b - b'A' + 10,
            _ => return None,
        };
        value = (value << 4) | nib as u64;
    }
    Some(value)
}

fn strip_cr(line: &[u8]) -> &[u8] {
    match line.split_last() {
        Some((b'\r', rest)) => rest,
        _ => line,
    }
}

#[derive(Clone, Copy)]
enum Current {
    /// No `fighter` line yet.
    Start,
    /// The last `fighter` line was rejected.
    Skipping,
    At(usize),
}

/// Parse a whole file into `out`, which must be freshly made (and may have had
/// [`Presets::init_named`] called). Lines end with `\n` or `\r\n`. On any state other than
/// [`FileState::Ok`] nothing is stored.
///
/// The file is read as bytes: everything the format means is ASCII, so a non-ASCII byte in
/// a comment is harmless and one in a field makes that field invalid.
pub fn parse(bytes: &[u8], out: &Presets) -> Report {
    let mut report = Report::new();
    if bytes.len() > MAX_FILE {
        report.state = FileState::TooLarge;
        return report;
    }
    // A final newline does not start another line.
    let body = match bytes.split_last() {
        Some((b'\n', rest)) => rest,
        _ => bytes,
    };
    let mut current = Current::Start;
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
                return report;
            }
            continue;
        }
        let text = line.split(|b| *b == b'#').next().unwrap_or(&[]);
        let mut fields = text.split(|b| *b == b' ' || *b == b'\t').filter(|f| !f.is_empty());
        let first = match fields.next() {
            Some(first) => first,
            None => continue,
        };
        if first == b"fighter" {
            // Whatever is wrong with this line, the lines after it are not the previous
            // preset's.
            current = Current::Skipping;
            let made = match (fields.next(), fields.next(), fields.next()) {
                (Some(name), Some(kind), None) => {
                    if !valid_name(name) {
                        Err(Reject::BadName)
                    } else {
                        match parse_hash(kind) {
                            Some(kind) => out.begin(name, kind),
                            None => Err(Reject::BadHash),
                        }
                    }
                }
                _ => Err(Reject::FieldCount),
            };
            match made {
                Ok(preset) => {
                    current = Current::At(preset);
                    report.presets += 1;
                }
                Err(why) => report.reject(number, why),
            }
            continue;
        }
        let stored = match (fields.next(), fields.next()) {
            (Some(value), None) => match parse_hash(first) {
                Some(0) | None => Err(Reject::BadHash),
                Some(hash) => match parse_decimal_bytes(value) {
                    None => Err(Reject::BadValue),
                    Some(value) => match current {
                        Current::Start => Err(Reject::NoPreset),
                        Current::Skipping => {
                            report.skipped = report.skipped.wrapping_add(1);
                            continue;
                        }
                        Current::At(preset) => out.set_field(preset, hash, value),
                    },
                },
            },
            _ => Err(Reject::FieldCount),
        };
        match stored {
            Ok(()) => report.fields += 1,
            Err(why) => report.reject(number, why),
        }
    }
    report.lines = number;
    report
}
