//! Side-B's owned Mythra status allocation and donor callback topology.
//! Not installed until the complete owned move and dependencies are available.
use smash::{lib::{lua_const::*, L2CValue}, lua2cpp::L2CFighterCommon};
use smashline::{Agent, Pre, Main, End, Exec, CheckAttack};

pub(super) const ATTACK1: i32 = 0x1fa;
pub(super) const ATTACK2: i32 = 0x1fb;
pub(super) const ATTACK3: i32 = 0x1fc;
pub(super) const APPEND: i32 = 0x1fd;
pub(super) const HOLD: i32 = 0x1fe;

type Status = unsafe extern "C" fn(&mut L2CFighterCommon) -> L2CValue;
type AttackCheck = unsafe extern "C" fn(
    &mut L2CFighterCommon, &L2CValue, &L2CValue,
) -> L2CValue;

pub(super) struct Basic {
    pub pre: Status,
    pub main: Status,
    pub end: Status,
}

pub(super) struct Attack {
    pub basic: Basic,
    pub exec: Status,
    pub check_attack: AttackCheck,
}

pub(super) struct Callbacks {
    pub entry: Basic,
    pub hold: Basic,
    pub hold_exec: Status,
    pub attack1: Attack,
    pub attack2: Attack,
    pub attack3: Basic,
    pub append: Attack,
}

/// All 25 donor registrations, with recipient IDs and install-time costume gate.
/// ATTACK3 deliberately has neither EXEC_STATUS nor CHECK_ATTACK.
pub(super) fn install(callbacks: Callbacks) {
    unsafe {
        assert_eq!(*FIGHTER_ELIGHT_STATUS_KIND_NUM + 9, ATTACK1,
                   "Hero side-B allocation disagrees with Mythra's native status limit");
        let mut agent = Agent::new("elight");
        agent.set_costume(crate::TARGET_COSTUMES.to_vec());
        agent.status(Pre, *FIGHTER_STATUS_KIND_SPECIAL_S, callbacks.entry.pre);
        agent.status(Main, *FIGHTER_STATUS_KIND_SPECIAL_S, callbacks.entry.main);
        agent.status(End, *FIGHTER_STATUS_KIND_SPECIAL_S, callbacks.entry.end);
        agent.status(Pre, HOLD, callbacks.hold.pre);
        agent.status(Main, HOLD, callbacks.hold.main);
        agent.status(End, HOLD, callbacks.hold.end);
        agent.status(Exec, HOLD, callbacks.hold_exec);
        for (id, callback) in [(ATTACK1, callbacks.attack1),
                               (ATTACK2, callbacks.attack2),
                               (APPEND, callbacks.append)] {
            agent.status(Pre, id, callback.basic.pre);
            agent.status(Main, id, callback.basic.main);
            agent.status(End, id, callback.basic.end);
            agent.status(Exec, id, callback.exec);
            agent.status(CheckAttack, id, callback.check_attack);
        }
        agent.status(Pre, ATTACK3, callbacks.attack3.pre);
        agent.status(Main, ATTACK3, callbacks.attack3.main);
        agent.status(End, ATTACK3, callbacks.attack3.end);
        agent.install();
    }
}
