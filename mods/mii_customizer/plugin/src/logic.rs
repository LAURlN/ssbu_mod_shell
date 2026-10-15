//! Pure logic of the 0.3.0 preset build: constants, the override decision, the re-entry
//! guard, line formatting, counters and the table of seen fighters. No skyline items, no
//! heap, no locks, no panicking paths, so the same file is compiled into a host-side test
//! (`scratch/2026-10-05_P7-PRESET-ENGINE/host_test.rs`).

use crate::loadout::{Src, Store};
use crate::preset::Presets;
use core::sync::atomic::{AtomicU32, AtomicU64, Ordering};

/// `FIGHTER_KIND_MIIGUNNER` on 13.0.4: the binding's constant, confirmed on the console
/// (`evidence/2026-10-05_gate2/RESULT.md`, every Gunner line `kind=74`).
pub const KIND_MIIGUNNER: i32 = 0x4a;
/// Contract C: the fighter kinds whose saved Miis can get a loadout. Add kinds here.
pub const ACCEPTED_KINDS: [i32; 1] = [KIND_MIIGUNNER];

/// Static per-player tables (P2-MATCH-READER; console-confirmed for local players 0 and 1,
/// `evidence/2026-10-04_gate1/RESULT.md`). Module-relative, inside `.bss`.
pub const TABLE_BASE: usize = 0x530_7760;
pub const ID_OFFSET: usize = 0xe58;
pub const ID_STRIDE: usize = 0x240;
pub const SPECIAL_OFFSET: usize = 0xa2;
pub const SPECIAL_STRIDE: usize = 0x1c8;
pub const PLAYERS: usize = 8;

/// Vtable of the 0x98-byte object built at 0x688508 with `[obj+8] = parent` and stored at
/// `[parent+0x50]`. Only requests on objects of this vtable can be overridden.
pub const VTABLE_WORK: usize = 0x4f8_9490;
/// The second vtable that shares the slot functions; for it `[x0+8]` is not shown to be a
/// parent, so it is only reported (`vt=2`).
pub const VTABLE_OTHER: usize = 0x4f7_3738;
/// Offset of the back-pointer inside the parent (`str x20,[x19,#0x50]` @0x688584).
pub const PARENT_WORK_OFFSET: usize = 0x50;

/// L3 lines per seen fighter: the first request of each of at most this many field hashes.
pub const L3_HASHES_PER_PARENT: u32 = 16;
/// Seen fighters (parent + identity) remembered per boot.
pub const SEEN_SLOTS: usize = 64;
/// First periodic L5 after this many requests, then after every doubling.
pub const L5_FIRST: u32 = 600;
/// Threads that can be inside the identity lookup at the same time.
pub const GUARD_SLOTS: usize = 8;

/// One hook site: module-relative offset and the four instruction words that must be
/// there before the hook is installed. `repr(C)` so the record is findable in the NRO.
#[repr(C)]
pub struct Site {
    pub offset: u64,
    pub words: [u32; 4],
}

/// research/P3-DIAG-PLUGIN.md step 0b, measured on main.bin sha256 f70c97d2...; confirmed
/// on the console by the 0.1.0 and 0.2.0 L0 lines.
///   ldr x0,[x0,#0x38] ; ldr x8,[x0] ; ldr x3,[x8,#0x30] ; br x3
pub const SITE_PARAM: Site = Site {
    offset: 0x4e_53e0,
    words: [0xf940_1c00, 0xf940_0008, 0xf940_1903, 0xd61f_0060],
};

pub fn words_equal(found: &[u32; 4], expected: &[u32; 4]) -> bool {
    let mut same = true;
    let mut i = 0;
    while i < 4 {
        same &= found[i] == expected[i];
        i += 1;
    }
    same
}

/// Runtime address of player `p`'s saved-fighter u32 ID, `None` when `p` is out of range.
pub fn id_addr(base: usize, p: u32) -> Option<usize> {
    if (p as usize) < PLAYERS {
        Some(base.wrapping_add(TABLE_BASE + ID_OFFSET + p as usize * ID_STRIDE))
    } else {
        None
    }
}

/// Runtime address of player `p`'s four special bytes, `None` when `p` is out of range.
pub fn special_addr(base: usize, p: u32) -> Option<usize> {
    if (p as usize) < PLAYERS {
        Some(base.wrapping_add(TABLE_BASE + SPECIAL_OFFSET + p as usize * SPECIAL_STRIDE))
    } else {
        None
    }
}

/// Which of the two audited vtables an object has: 1 = [`VTABLE_WORK`], 2 =
/// [`VTABLE_OTHER`], 0 = neither (or the module base is unknown).
pub fn vtable_class(base: usize, vtable: u64) -> u32 {
    if base == 0 {
        0
    } else if vtable == base.wrapping_add(VTABLE_WORK) as u64 {
        1
    } else if vtable == base.wrapping_add(VTABLE_OTHER) as u64 {
        2
    } else {
        0
    }
}

/// Outcome of one request. Everything except `Ok` returns the original value untouched.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
#[repr(u8)]
pub enum St {
    /// Override applied.
    Ok = 0,
    /// No usable loadout table (no file, bad file, or no accepted entry).
    Off,
    /// `x0` is null or its vtable is not [`VTABLE_WORK`].
    Vtable,
    /// `[x0+8]` is null.
    NoParent,
    /// `[parent+0x50] != x0`.
    BackPtr,
    /// This thread is already inside the identity lookup.
    Reentry,
    /// All guard slots are taken by other threads.
    GuardFull,
    /// The parent's object id does not have the fighter category.
    Category,
    /// The object registered under that id has another module accessor.
    RoundTrip,
    /// The game reports another category for that id.
    Category2,
    /// Kind by accessor and kind by object id differ.
    KindMismatch,
    /// Entry id by accessor and entry id by object id differ.
    EntryMismatch,
    /// Entry id outside 0..7.
    EntryRange,
    /// A fighter, but not of a kind in [`ACCEPTED_KINDS`].
    NotGunner,
    /// The player's saved-fighter slot holds 0.
    NoSlotId,
    /// No explicit value and no preset value for this saved fighter and field.
    NoEntry,
}

pub const ST_COUNT: usize = 16;

impl St {
    pub fn name(self) -> &'static str {
        match self {
            St::Ok => "ok",
            St::Off => "off",
            St::Vtable => "vt",
            St::NoParent => "nopar",
            St::BackPtr => "back",
            St::Reentry => "reent",
            St::GuardFull => "gfull",
            St::Category => "cat",
            St::RoundTrip => "rt",
            St::Category2 => "cat2",
            St::KindMismatch => "kindx",
            St::EntryMismatch => "entx",
            St::EntryRange => "entr",
            St::NotGunner => "kind",
            St::NoSlotId => "noid",
            St::NoEntry => "noent",
        }
    }
}

/// What is known about the fighter behind a request. `kind` and `player` are -1 when
/// unknown; `st` is the reason the identity is unknown, or `Ok`.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct Ident {
    pub st: St,
    pub kind: i32,
    pub player: i32,
}

impl Ident {
    pub const fn unknown(st: St) -> Self {
        Ident { st, kind: -1, player: -1 }
    }
}

/// Pointer checks of condition 1. `vt_class` from [`vtable_class`].
pub fn pointer_guard(x0: u64, vt_class: u32, parent: u64, back: u64) -> St {
    if x0 == 0 || vt_class != 1 {
        St::Vtable
    } else if parent == 0 {
        St::NoParent
    } else if back != x0 {
        St::BackPtr
    } else {
        St::Ok
    }
}

/// What the game reported about one parent, gathered by the hook through the binding.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct Facts {
    /// The binding's fighter category constant.
    pub fighter_cat: i32,
    /// Category from the accessor's object id.
    pub cat_accessor: i32,
    /// The object registered under that id has this parent as its module accessor.
    pub round_trip: bool,
    /// Category the game reports for the id.
    pub cat_object: i32,
    pub kind_accessor: i32,
    pub kind_object: i32,
    pub entry_accessor: i32,
    pub entry_object: i32,
}

/// Condition 2 without the kind test: is this parent a fighter with one consistent kind
/// and an entry id in 0..7?
pub fn identify(f: &Facts) -> Ident {
    if f.cat_accessor != f.fighter_cat {
        return Ident::unknown(St::Category);
    }
    if !f.round_trip {
        return Ident::unknown(St::RoundTrip);
    }
    if f.cat_object != f.fighter_cat {
        return Ident::unknown(St::Category2);
    }
    if f.kind_accessor != f.kind_object {
        return Ident::unknown(St::KindMismatch);
    }
    if f.entry_accessor != f.entry_object {
        return Ident { st: St::EntryMismatch, kind: f.kind_accessor, player: -1 };
    }
    if f.entry_accessor < 0 || f.entry_accessor >= PLAYERS as i32 {
        return Ident { st: St::EntryRange, kind: f.kind_accessor, player: -1 };
    }
    Ident { st: St::Ok, kind: f.kind_accessor, player: f.entry_accessor }
}

/// Result of [`decide`]. `value` and `src` are `Some` only together with `st == Ok`.
#[derive(Clone, Copy, PartialEq, Debug)]
pub struct Decision {
    pub st: St,
    /// Loadout entry index, for the once-per-(id, field) `OV` line.
    pub entry: usize,
    pub value: Option<f32>,
    pub src: Option<Src>,
}

impl Decision {
    pub const fn vanilla(st: St) -> Self {
        Decision { st, entry: 0, value: None, src: None }
    }
}

/// Contract C and the resolution of contract B: a resolved fighter of an accepted kind
/// whose player slot holds a non-zero saved-fighter ID, and a value for field index `field`
/// from that ID's explicit line or, failing that, its preset. `slot_id` is read by the
/// caller only when `ident.player` is valid.
pub fn decide(ident: &Ident, kinds: &[i32], slot_id: u32, store: &Store, presets: &Presets, field: usize) -> Decision {
    if ident.st != St::Ok {
        return Decision::vanilla(ident.st);
    }
    if !kinds.contains(&ident.kind) {
        return Decision::vanilla(St::NotGunner);
    }
    if ident.player < 0 || ident.player >= PLAYERS as i32 {
        return Decision::vanilla(St::EntryRange);
    }
    if slot_id == 0 {
        return Decision::vanilla(St::NoSlotId);
    }
    match store.resolve(slot_id, field, presets) {
        Some(hit) => Decision { st: St::Ok, entry: hit.entry, value: Some(hit.value), src: Some(hit.src) },
        None => Decision::vanilla(St::NoEntry),
    }
}

/// Never-zero key of one fighter as the log sees it: the parent address together with
/// what was resolved about it (kind, player, saved-fighter ID). A parent address reused by
/// another fighter in a later match, or an identity that resolves late, gives a new key.
/// Logging only; nothing is cached for the decision itself.
pub fn seen_key(parent: u64, ident: &Ident, slot_id: u32) -> u64 {
    let who = ((slot_id as u64) << 32) | (((ident.kind as u64) & 0xffff) << 16) | ((ident.player as u64) & 0xffff);
    (parent.wrapping_mul(0x9e37_79b9_7f4a_7c15) ^ who.wrapping_mul(0xc2b2_ae3d_27d4_eb4f)) | 1
}

/// Result of [`ThreadGuard::enter`].
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Enter {
    /// Entered; pass the slot to [`ThreadGuard::leave`].
    Entered(usize),
    /// This thread is already inside.
    Reentry,
    /// No free slot (or the thread id is unknown).
    Full,
}

/// Per-thread re-entry guard without thread-local storage: a small set of thread ids
/// that are currently inside the guarded section. Never waits.
pub struct ThreadGuard {
    slots: [AtomicU64; GUARD_SLOTS],
}

impl ThreadGuard {
    pub const fn new() -> Self {
        ThreadGuard { slots: [KEY_ZERO; GUARD_SLOTS] }
    }

    /// `tid` must be non-zero and unique per live thread.
    pub fn enter(&self, tid: u64) -> Enter {
        if tid == 0 {
            return Enter::Full;
        }
        // Only this thread ever stores `tid`, so this scan cannot race with itself.
        if self.slots.iter().any(|slot| slot.load(Ordering::Acquire) == tid) {
            return Enter::Reentry;
        }
        for (i, slot) in self.slots.iter().enumerate() {
            if slot.compare_exchange(0, tid, Ordering::AcqRel, Ordering::Acquire).is_ok() {
                return Enter::Entered(i);
            }
        }
        Enter::Full
    }

    pub fn leave(&self, slot: usize) {
        if let Some(cell) = self.slots.get(slot) {
            cell.store(0, Ordering::Release);
        }
    }
}

/// Count one event and say whether it is still among the first `limit`.
/// Returns the 1-based event number.
pub fn count_event(counter: &AtomicU32, limit: u32) -> (u32, bool) {
    let n = counter.fetch_add(1, Ordering::Relaxed).wrapping_add(1);
    (n, n != 0 && n <= limit)
}

/// True when the 1-based request number `n` is [`L5_FIRST`] times a power of two.
pub fn totals_due(n: u32) -> bool {
    n >= L5_FIRST && n % L5_FIRST == 0 && (n / L5_FIRST).is_power_of_two()
}

/// Result of [`SeenTable::observe`].
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct Seen {
    /// Table slot, `None` when [`SEEN_SLOTS`] other keys were already stored.
    pub slot: Option<usize>,
    /// This call inserted the key.
    pub is_new: bool,
    /// This is the first request of this field for the key, and the key has had no more
    /// than [`L3_HASHES_PER_PARENT`] such firsts.
    pub log: bool,
}

/// Lock-free set of at most [`SEEN_SLOTS`] keys ([`seen_key`]) with, per key, the set of
/// field indexes already seen. Used for logging only; the override decision never reads
/// it. Key 0 means "empty".
pub struct SeenTable {
    keys: [AtomicU64; SEEN_SLOTS],
    fields: [AtomicU64; SEEN_SLOTS],
    logged: [AtomicU32; SEEN_SLOTS],
    distinct: AtomicU32,
    overflow: AtomicU32,
}

const KEY_ZERO: AtomicU64 = AtomicU64::new(0);
const COUNT_ZERO: AtomicU32 = AtomicU32::new(0);

impl SeenTable {
    pub const fn new() -> Self {
        SeenTable {
            keys: [KEY_ZERO; SEEN_SLOTS],
            fields: [KEY_ZERO; SEEN_SLOTS],
            logged: [COUNT_ZERO; SEEN_SLOTS],
            distinct: AtomicU32::new(0),
            overflow: AtomicU32::new(0),
        }
    }

    pub fn observe(&self, key: u64, field: usize) -> Seen {
        let key = if key == 0 { u64::MAX } else { key };
        let mut found: Option<usize> = None;
        let mut is_new = false;
        for (i, slot) in self.keys.iter().enumerate() {
            let cur = slot.load(Ordering::Acquire);
            if cur == key {
                found = Some(i);
                break;
            }
            if cur == 0 {
                match slot.compare_exchange(0, key, Ordering::AcqRel, Ordering::Acquire) {
                    Ok(_) => {
                        found = Some(i);
                        is_new = true;
                        break;
                    }
                    Err(other) => {
                        if other == key {
                            found = Some(i);
                            break;
                        }
                    }
                }
            }
        }
        let cells = found.and_then(|i| self.fields.get(i).zip(self.logged.get(i)));
        match (found, cells) {
            (Some(i), Some((fields, logged))) if field < 64 => {
                if is_new {
                    self.distinct.fetch_add(1, Ordering::Relaxed);
                }
                let bit = 1u64 << field;
                // The plain load keeps the common case (field already seen) free of writes.
                let first = fields.load(Ordering::Relaxed) & bit == 0 && fields.fetch_or(bit, Ordering::AcqRel) & bit == 0;
                let log = first && count_event(logged, L3_HASHES_PER_PARENT).1;
                Seen { slot: Some(i), is_new, log }
            }
            _ => {
                self.overflow.fetch_add(1, Ordering::Relaxed);
                Seen { slot: None, is_new: false, log: false }
            }
        }
    }

    pub fn distinct(&self) -> u32 {
        self.distinct.load(Ordering::Relaxed)
    }

    /// Requests whose key did not fit in the table.
    pub fn overflow(&self) -> u32 {
        self.overflow.load(Ordering::Relaxed)
    }
}

/// Bit set of field indexes with "set once" semantics: the first request of a field, the
/// first `x2 != 0` request of a field.
pub struct FieldFlags(AtomicU64);

impl FieldFlags {
    pub const fn new() -> Self {
        FieldFlags(AtomicU64::new(0))
    }

    /// True exactly once per field index below 64.
    #[inline(always)]
    pub fn first(&self, field: usize) -> bool {
        if field >= 64 {
            return false;
        }
        let bit = 1u64 << field;
        self.0.load(Ordering::Relaxed) & bit == 0 && self.0.fetch_or(bit, Ordering::Relaxed) & bit == 0
    }

    #[allow(dead_code)]
    pub fn get(&self) -> u64 {
        self.0.load(Ordering::Relaxed)
    }
}

/// Fixed-size text buffer. Writes past the end are dropped; the last byte is kept free
/// so `end_line` can always terminate a truncated line.
pub struct LineBuf<const N: usize> {
    buf: [u8; N],
    len: usize,
}

impl<const N: usize> LineBuf<N> {
    pub const fn new() -> Self {
        LineBuf { buf: [0; N], len: 0 }
    }

    pub fn as_bytes(&self) -> &[u8] {
        self.buf.get(..self.len).unwrap_or(&[])
    }

    fn push(&mut self, b: u8) {
        if self.len + 1 < N {
            if let Some(slot) = self.buf.get_mut(self.len) {
                *slot = b;
                self.len += 1;
            }
        }
    }

    pub fn s(&mut self, text: &str) -> &mut Self {
        self.bytes(text.as_bytes())
    }

    pub fn bytes(&mut self, text: &[u8]) -> &mut Self {
        for &b in text {
            self.push(b);
        }
        self
    }

    /// `0x` + lower-case hex without leading zeros.
    pub fn hex(&mut self, v: u64) -> &mut Self {
        self.s("0x");
        let mut started = false;
        let mut shift = 60i32;
        while shift >= 0 {
            let nib = ((v >> shift) & 0xf) as u8;
            if nib != 0 || started || shift == 0 {
                started = true;
                self.push(hex_digit(nib));
            }
            shift -= 4;
        }
        self
    }

    /// Exactly `digits` lower-case hex digits, no prefix.
    pub fn hex_fixed(&mut self, v: u64, digits: u32) -> &mut Self {
        let mut i = digits.min(16);
        while i > 0 {
            i -= 1;
            self.push(hex_digit(((v >> (i * 4)) & 0xf) as u8));
        }
        self
    }

    /// A 40-bit param hash as the preset file writes it: `0x` + ten hex digits.
    pub fn hash40(&mut self, hash: u64) -> &mut Self {
        self.s("0x").hex_fixed(hash, 10)
    }

    pub fn dec(&mut self, mut v: u64) -> &mut Self {
        let mut tmp = [0u8; 20];
        let mut n = 0;
        loop {
            if let Some(slot) = tmp.get_mut(n) {
                *slot = b'0' + (v % 10) as u8;
            }
            n += 1;
            v /= 10;
            if v == 0 || n >= 20 {
                break;
            }
        }
        while n > 0 {
            n -= 1;
            if let Some(&b) = tmp.get(n) {
                self.push(b);
            }
        }
        self
    }

    /// Signed decimal.
    pub fn int(&mut self, v: i64) -> &mut Self {
        if v < 0 {
            self.s("-");
        }
        self.dec(v.unsigned_abs())
    }

    /// Decimal with four fraction digits; `nan`, `inf`, or `big` beyond +-4e9.
    /// The raw bits are logged separately, this is for reading only.
    pub fn f32_dec(&mut self, v: f32) -> &mut Self {
        if v != v {
            return self.s("nan");
        }
        let neg = v < 0.0;
        let a = if neg { -v } else { v };
        if neg {
            self.s("-");
        }
        if a > 3.4e38 {
            return self.s("inf");
        }
        if a >= 4.0e9 {
            return self.s("big");
        }
        let mut whole = a as u64;
        let mut frac = ((a - whole as f32) * 10000.0 + 0.5) as u64;
        if frac >= 10000 {
            whole += 1;
            frac -= 10000;
        }
        self.dec(whole).s(".");
        self.push(b'0' + ((frac / 1000) % 10) as u8);
        self.push(b'0' + ((frac / 100) % 10) as u8);
        self.push(b'0' + ((frac / 10) % 10) as u8);
        self.push(b'0' + (frac % 10) as u8);
        self
    }

    /// Terminate the current line. Always succeeds, even after truncation.
    pub fn end_line(&mut self) -> &mut Self {
        if let Some(slot) = self.buf.get_mut(self.len) {
            *slot = b'\n';
            self.len += 1;
        } else if let Some(slot) = self.buf.get_mut(N.wrapping_sub(1)) {
            *slot = b'\n';
        }
        self
    }
}

fn hex_digit(nib: u8) -> u8 {
    if nib < 10 {
        b'0' + nib
    } else {
        b'a' + (nib - 10)
    }
}

/// `|pK=<id>:<b0b1b2b3>` for one player of the L4 line.
pub fn push_player<const N: usize>(out: &mut LineBuf<N>, p: u32, id: u32, special: [u8; 4]) {
    out.s("|p").dec(p as u64).s("=").hex_fixed(id as u64, 8).s(":");
    for b in special.iter() {
        out.hex_fixed(*b as u64, 2);
    }
}
