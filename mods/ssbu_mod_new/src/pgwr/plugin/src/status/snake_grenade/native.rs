//! Authorized route A fuse bridge. Full leaf pinned in life_native.json.
//! Runtime behavior remains unverified. The installed frameworks are untouched.
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
#[path = "native_signatures.rs"]
mod native_signatures;
static READY: AtomicBool = AtomicBool::new(false);
static BASE: AtomicUsize = AtomicUsize::new(0);
static LOGS: AtomicUsize = AtomicUsize::new(0);

// C-ABI QueryMemory stub preserves the syscall's secondary output.
core::arch::global_asm!(
    ".section .text.pgwr_snake_query_memory, \"ax\", %progbits",
    ".global pgwr_snake_query_memory", ".hidden pgwr_snake_query_memory",
    ".type pgwr_snake_query_memory, %function",
    ".p2align 2", "pgwr_snake_query_memory:",
    "str x1, [sp, #-16]!", "svc 0x6", "ldr x2, [sp], #16", "str w1, [x2]", "ret",
    ".size pgwr_snake_query_memory, .-pgwr_snake_query_memory",
);
extern "C" { fn pgwr_snake_query_memory(info: *mut u64, page: *mut u32, address: usize) -> u32; }
pub(super) unsafe fn mapped(address: usize, size: usize) -> bool {
    let Some(end) = address.checked_add(size) else { return false };
    if address < 0x10000 { return false; }
    let mut info = [0u64; 6];
    let mut page = 0u32;
    pgwr_snake_query_memory(info.as_mut_ptr(), &mut page, address) == 0
        && info[3] as u32 & 1 != 0 && address as u64 >= info[0]
        && end as u64 <= info[0].saturating_add(info[1])
}

#[skyline::hook(offset = 0x1674e90)]
unsafe fn life() -> i32 {
    let manager_slot = BASE.load(Ordering::Acquire) + 0x52bb3b0;
    if !mapped(manager_slot, 8) { crate::diagnostic!(super::log("FAIL life manager slot unreadable".into())); return super::params::GRENADE_LIFE; }
    let manager = *(manager_slot as *const usize);
    if mapped(manager.saturating_add(0x7e0), 8) {
        let donor = *((manager + 0x7e0) as *const usize);
        if donor != 0 {
            // Validate the original leaf's remaining dereferences before calling it.
            if mapped(donor.saturating_add(0xf0), 8) {
                let value = *((donor + 0xf0) as *const usize);
                if mapped(value, 4) { return original!()(); }
            }
            crate::diagnostic!(super::log("FAIL life donor parameter chain unreadable".into()));
        }
    }
    if LOGS.fetch_add(1, Ordering::Relaxed) < 8 {
        crate::diagnostic!(super::log(format!("FUSE owned life={} Snake parameter unavailable", super::params::GRENADE_LIFE)));
    }
    super::params::GRENADE_LIFE
}

pub fn ready() -> bool { READY.load(Ordering::Acquire) }
pub unsafe fn install() -> bool {
    let base = crate::article::game_base() as usize;
    for &(offset, signature) in native_signatures::SIGNATURES {
        let address = base.saturating_add(offset);
        if !mapped(address, signature.len()) || std::slice::from_raw_parts(address as *const u8, signature.len()) != signature {
            crate::diagnostic!(super::log(format!("FAIL native 13.0.4 signature offset={:#x}; pull disabled", offset)));
            return false;
        }
    }
    BASE.store(base, Ordering::Release);
    skyline::install_hooks!(life);
    READY.store(true, Ordering::Release);
    crate::diagnostic!(super::log("READY life bridge 13.0.4 signature verified; owned life=150".into()));
    true
}
