//! Names used in the trace's `object` column, and clone -> base kind mapping.
//!
//! The object column must be identical for the vanilla fighter and its clone, so
//! clone kinds are reported under their *base* fighter's name.
use core::sync::atomic::{AtomicUsize, Ordering};

pub const KIND_EFLAME: i32 = 90;
pub const KIND_ELIGHT: i32 = 91;

/// Base fighter names for the kinds this project cares about. Other fighters are
/// written as `k<kind>`, which is enough to keep them apart in a comparison.
pub fn fighter_name(kind: i32) -> String {
    match kind {
        KIND_EFLAME => "eflame".into(),
        KIND_ELIGHT => "elight".into(),
        _ => format!("k{}", kind),
    }
}

/// Weapon kinds of Pyra/Mythra and the shared Element articles, from Astra's
/// class inventory (reports/native-classes.json). Names follow the game's
/// `<owner>_<article>` convention. Unknown kinds are written as `w<kind>`.
pub fn weapon_name(kind: i32) -> String {
    let name = match kind {
        463 => "element_changer",
        464 => "element_diver",
        588 => "eflame_esword",
        589 => "eflame_firepillar",
        590 => "eflame_blazepillar",
        591 => "eflame_windummy",
        592 => "eflame_winsword",
        593 => "elight_esword",
        594 => "elight_bunshin",
        595 => "elight_exprosiveshot",
        596 => "elight_spreadbullet",
        597 => "elight_meteor",
        598 => "elight_beam",
        599 => "elight_windummy",
        600 => "elight_winsword",
        _ => return format!("w{}", kind),
    };
    name.into()
}

// 0 = not looked up yet, 1 = Clone Engine not loaded, anything else = function address.
static BASE_KIND_FN: AtomicUsize = AtomicUsize::new(0);

/// Maps a Clone Engine fighter kind to its base kind; vanilla kinds map to themselves.
/// Uses Clone Engine's exported `clone_engine_get_base_kind` when that plugin is loaded.
pub unsafe fn base_fighter_kind(kind: i32) -> i32 {
    let mut f = BASE_KIND_FN.load(Ordering::Relaxed);
    if f == 0 {
        let mut address: usize = 0;
        skyline::nn::ro::LookupSymbol(&mut address, "clone_engine_get_base_kind\0".as_ptr());
        f = if address == 0 { 1 } else { address };
        BASE_KIND_FN.store(f, Ordering::Relaxed);
    }
    if f == 1 {
        return kind;
    }
    let get: extern "C" fn(i32) -> i32 = core::mem::transmute(f);
    let base = get(kind);
    if base >= 0 { base } else { kind }
}
