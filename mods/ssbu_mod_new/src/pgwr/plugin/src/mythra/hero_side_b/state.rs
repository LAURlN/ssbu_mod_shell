//! Owned move state; only generic fighter entry/color IDs are read on Mythra.
//! These fields never alias Hero's work IDs, and contain no mana state.
use smash::{app::{self, lua_bind::*, BattleObjectModuleAccessor}, lib::lua_const::*};
use std::sync::atomic::{AtomicI32, AtomicU32, Ordering};

pub(super) const ACTIVATE_LIGHTNING: u32 = 1 << 0;
pub(super) const ENABLE_SPARK: u32 = 1 << 1;
pub(super) const DECIDE_SPARK_RIGHT: u32 = 1 << 2;
pub(super) const DECIDE_SPARK_LEFT: u32 = 1 << 3;
pub(super) const FINISH_SPARK_RIGHT: u32 = 1 << 4;
pub(super) const FINISH_SPARK_LEFT: u32 = 1 << 5;
pub(super) const STORE_TARGET_RIGHT: u32 = 1 << 6;
pub(super) const STORE_TARGET_LEFT: u32 = 1 << 7;
pub(super) const CALL_EXPLOSION: u32 = 1 << 8;
/// Owned replacement for the donor's native "has the bolt struck" link-event query.
pub(super) const LIGHTNING_ARRIVED: u32 = 1 << 9;

pub(super) struct Target {
    pub x: AtomicU32,
    pub y: AtomicU32,
    pub priority: AtomicI32,
    pub wait_frames: AtomicI32,
}
impl Target {
    const fn new() -> Self {
        Self { x: AtomicU32::new(0), y: AtomicU32::new(0),
               priority: AtomicI32::new(99), wait_frames: AtomicI32::new(0) }
    }
    fn reset(&self) {
        self.x.store(0, Ordering::Relaxed);
        self.y.store(0, Ordering::Relaxed);
        self.priority.store(99, Ordering::Relaxed);
        self.wait_frames.store(0, Ordering::Relaxed);
    }
}

pub(super) struct State {
    pub flags: AtomicU32,
    pub hold_frames: AtomicI32,
    pub right: Target,
    pub left: Target,
    pub generate_x: AtomicU32,
    pub generate_y: AtomicU32,
    pub generate_lr: AtomicU32,
    pub lightning_offset_x: AtomicU32,
    pub lightning_count: AtomicI32,
    pub lightning_interval: AtomicI32,
    pub lightning_team: AtomicI32,
    pub lightning_owner: AtomicU32,
    // Instance lifetime: never clear these merely because a new move starts.
    pub spark_log_group: AtomicI32,
    pub spark_log_references: AtomicI32,
    pub lightning_log_group: AtomicI32,
    pub lightning_log_references: AtomicI32,
}
impl State {
    const fn new() -> Self {
        Self { flags: AtomicU32::new(0), hold_frames: AtomicI32::new(0),
               right: Target::new(), left: Target::new(),
               generate_x: AtomicU32::new(0), generate_y: AtomicU32::new(0),
               generate_lr: AtomicU32::new(0), lightning_offset_x: AtomicU32::new(0),
               lightning_count: AtomicI32::new(0), lightning_interval: AtomicI32::new(0),
               lightning_team: AtomicI32::new(-1), lightning_owner: AtomicU32::new(u32::MAX),
               spark_log_group: AtomicI32::new(-1), spark_log_references: AtomicI32::new(0),
               lightning_log_group: AtomicI32::new(-1), lightning_log_references: AtomicI32::new(0) }
    }
    pub fn flag(&self, bit: u32) -> bool { self.flags.load(Ordering::Relaxed) & bit != 0 }
    pub fn set(&self, bit: u32) { self.flags.fetch_or(bit, Ordering::Relaxed); }
    pub fn clear(&self, bit: u32) { self.flags.fetch_and(!bit, Ordering::Relaxed); }
    pub fn start(&self, owner: u32, team: i32) {
        self.flags.store(0, Ordering::Relaxed);
        self.hold_frames.store(0, Ordering::Relaxed);
        self.right.reset();
        self.left.reset();
        self.generate_x.store(0, Ordering::Relaxed);
        self.generate_y.store(0, Ordering::Relaxed);
        self.generate_lr.store(0, Ordering::Relaxed);
        self.lightning_offset_x.store(0, Ordering::Relaxed);
        self.lightning_count.store(0, Ordering::Relaxed);
        self.lightning_interval.store(0, Ordering::Relaxed);
        self.lightning_owner.store(owner, Ordering::Relaxed);
        self.lightning_team.store(team, Ordering::Relaxed);
    }
}
static STATES: [State; 8] = [State::new(), State::new(), State::new(), State::new(),
                            State::new(), State::new(), State::new(), State::new()];

/// For valid engine-owned accessors only. Native interceptions must range-check
/// their pointer before calling this API; no arbitrary-pointer probe happens here.
pub(super) unsafe fn get(boma: *mut BattleObjectModuleAccessor) -> Option<&'static State> {
    if boma.is_null() || app::utility::get_category(&mut *boma) != *BATTLE_OBJECT_CATEGORY_FIGHTER
        || app::utility::get_kind(&mut *boma) != *FIGHTER_KIND_ELIGHT
        || !crate::TARGET_COSTUMES.contains(&(WorkModule::get_int(
            boma, *FIGHTER_INSTANCE_WORK_ID_INT_COLOR) as usize)) { return None; }
    let entry = WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID);
    if (0..8).contains(&entry) { Some(&STATES[entry as usize]) } else { None }
}
