# Grabs / catch boxes (Monkey Flip investigation)

## DK cargo boundary (2026-10-03)

**B: offline instruction/asset measurements; D: recipient semantics.**
`refs/donkey_cargo/ownership_contract.json` pins the reviewed cargo state graph,
native closure, parameters, exact victim callbacks and shared-pose boundary.
`DEPENDENCIES.json` retains the earlier research inventory. Collective request:
15 attacker states plus three victim roles per eligible fighter table; no IDs
selected for production. Private test 0x400..0x411 is audited independently of
donor IDs. Offline entry recovery: DK initializer writes global_table[0x45];
common grab dispatch and cleanup classify forward throw through that slot.
Pickup sends `shoulder` through the existing capture link; throws send
`shoulder_throw`. This supplies no authorization for constructing a new link.
The DK lift helper must not be called on eflame; its inspected branch toggles
the common lightweight flag and calls a default callback also found on Pyra.
The user explicitly authorized cargo-gated extensions at existing +0x170 and
+0x210 interception points, preserving Monkey Flip/G&W and forwarding others
(`refs/donkey_cargo/native_authorization.json`). Task runtime and an unapplied
integration patch now include those extensions. Offline native lookup follows
the existing capture parent to the captor MotionModule shared resources; Pickel
retains local overlays. Owned aliases retain all native victim template tracks
(26 or 67 by body variant), independently of the captor's bone intersection.
Exact native victim slots are Pre/Main/End/Init/Exit/CheckDamage (18 total),
without guessed Exec/MapCorrection. Wildcard status registration and concrete
fighter ACMD registration are separate framework requirements.
0.1.0 hardware A: user reported pickup, carrying/walking/jumping and grab release
successful. Cargo throws crashed; three reports show a null capture object during
stock victim Thrown shared-motion lookup at main+0x483130. Owned End/Exit cleanup
recognizes only custom next-state IDs, whereas native shoulder_throw queues the
stock thrown role before owned Pre routing. Premature link cleanup is the current
D diagnosis, pending a controlled retest. 0.1.1 changes only three owned cleanup
comparison sites to recognize queued stock carry/thrown semantic aliases.
Build/package checks and compiled scalar controls passed (B); corrected throws
and complete interruption/death/swap cleanup remain unverified (D).
Evidence: `evidence/2026-10-03_pgwr_dk_cargo-0.1.0-test_hardware/RESULT.md` and
`evidence/2026-10-03_pgwr_dk_cargo-0.1.1-test/RESULT.md`.

Eliminated by measurement: box exists (`CATCHBOX grab0/1/2=true`); cleared exactly on the donor schedule; arity;
grab module inactive (`set_rebound(true)`, `sleep(false)`, size mul, check_front all accepted and held); anchor `top`
reads back as fighter origin (engine-side anchor); the donor status scripts and ACMD omit the native receiver described below
(`SpecialSJump*` alone is not the complete capture path); hand-built `set_catch` + `LinkModule::link`
+ status request **freezes the console** (do not do it; `set_catch` alone gives `is_catch` but publishes no
`LINK_NO_CAPTURE` node and does not route the victim).

State in pgwr (2026-09-30, 0.15.1): the Monkey Flip port ships the donor's own two `CATCH` boxes and clear schedule and nothing else - no hand-arming of the grab module, no enlarged diagnostic box - and logs `GrabModule::is_grab`/`node` and the stored box centre at the donor's frames 7/19/26, `CatchModule::is_catch` on the leap, and (0.15.1) the victim's side of the capture every frame it could exist. Textbook 8-value `CATCH` calls cannot be emitted by the pinned `smash_script` macro at all (it always pushes 11, `None` = "no second point"), so the donor's call shape is not distinguishable from the macro's. (B)

## Native receiver missing from the port (2026-09-30)

**B, measured offline:** `tools/audit_mflip_capture_native.py` 1.1.0 on
`dumps/exefs/13.0.4/main.bin`, sha256
`f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`.
Pinned instructions and report: `refs/diddy_monkey_flip/{capture_native.json,
diddy_capture_receiver.asm,eflame_capture_receiver.asm}`. Smoke assertions pass.

Diddy's fighter-class vtable `0x4fa40f8`, slot +0x170, points to `0x956b70`.
Its `capture` dispatch checks event +0x38 = 0xf0 (CLUNG_DIDDY) and Diddy's own
attacker statuses 0x1e5/0x1ee, requests his cling 0x1e8, writes acceptance at
+0x28 and constraint at +0x4f, and passes sender +0x20 into CatchModule.
Link constraint setup and victim-dependent translated offset follow. The offset
branch continues after the first RET: first-RET-only disassembly misses it.
Exported module wrappers independently identify the status request, set_catch,
constraint flag and translated-offset calls. Pyra's corresponding slot points
to `0xa0c8d0`; its dispatch compares other event hashes, without a capture branch.
The pgwr port before 0.20.5 had status/ACMD callbacks without a native receiver equivalent.

**D, fix hypothesis:** the omitted receiver prevents completion of the capture
handshake. No receiver-present/receiver-absent hardware control exists, so this
is not an established cause. Adding an owned, gated equivalent and comparing
with stock Diddy, Pyra c00 and the ordinary standing grab would settle it.
The user authorized the native receiver, build and installation on 2026-09-30.
0.20.5 contains the owned translation in `src/pgwr/plugin/src/status/monkey_flip_capture.rs`,
with queued attacker status request, event acceptance, native catch setup and
constraint setup. Event/object ranges use SVC QueryMemory; calls are lock-free
with a thread-local re-entry guard. Full Pyra/Diddy receiver signatures gate installation.
`tools/gen_mflip_capture_data.py` 1.0.0 copies all 94 victim-kind offset triples
from `fighter_param_thrown.prc/diddy_special_s`; native decoder `0x816374..0x81638c`
selects the same +0x110 vector read by helper `0x721240`. Offsets and signatures
are pinned in `refs/diddy_monkey_flip/capture_owned_data.json`. Item senders are
refused; item-specific attachment branches are outside this fighter-grab test.
The controlled test is in `projects/pgwr/TODO.md`. Calling Diddy's handler on Pyra is not the proposed route:
its status gates and class fields are donor-specific.

## 0.20.5 hardware failure and next guard experiment (2026-09-30)

**A:** `evidence/2026-09-30_pgwr_0.20.5/RESULT.md` preserves the user's
"it didn't grab" verdict and the complete boot log. The receiver logged READY,
then 276 invalid event/fighter range refusals; no capture EVENT/ACCEPT/SETUP or
ported cling. Stock Diddy logged capture, cling and attack release. Ported victim
animation and attack/jump release remain untested because capture failed.
Nearest-opponent telemetry did not resolve the opponent, so contact was not measured.

**B:** `tools/audit_pgwr_svc_guard.py` 1.0.0 measures the compiled 0.20.6 ELF
in `builds/.cache/pgwr-target`; `builds/pgwr/0.20.6/capture_guard_audit.json`
pins its hash. The guard calls the five-instruction C-ABI QueryMemory stub from
smashline commit `be3ef308ed8e479922da192a391e0684184af2af`, rather than retaining
guard variables across an inline syscall. Rejected events forward to Pyra's
original receiver. Bounded RANGE logs include result, address, region and permission.
**D:** syscall register clobber is a candidate explanation for the old refusals;
the hardware log does not establish it. The 0.20.6 result supports the combined
guard/forwarding correction without isolating register clobber as its cause.

**A, 0.20.6:** `evidence/2026-09-30_pgwr_0.20.6/RESULT.md` records the user's
capture confirmation and T-posing grabbed opponents. Ten capture/accept/setup/cling
entries, 447 captured CLUNG_DIDDY victim samples, zero refusals. A motion hash
and advancing frames are present but do not establish the intended visual pose.
Both exits still need explicit confirmation. The user permits deferring the pose
issue if difficult; preserve capture while testing the separate aerial-use rules.

## Earlier victim-side evidence

The existing 0.20.2 card log records live boxes, `is_catch=false`, null capture
and no victim object; contact was not measured. 0.20.3 adds donor and nearest
opponent telemetry but has no recorded run. Earlier hand-set catch experiments
reported an attacker capture without victim routing; completing the link by hand
froze hardware. Neither experiment substitutes for the donor's native receiver.

Keep `VICTIM`, `VICTIMSTATUS`, `CATCH HANDOFF` and `CLING`: no grabbed status,
a grabbed status without a motion and a non-advancing grabbed motion are distinct
outcomes. An acceptance write is not successful capture: measure the published
link, victim status/motion/frame and release on both cling exits. Existing box
geometry and animation hypotheses remain open until a controlled reading; no
missing clip should be invented from an incomplete dump.

## Down throw: `ThrowLw` is not `AttackLw4`, and the prone victim is an attribute (2026-10-02)

**B for the numbers and the mechanism (measured against pinned vanilla 13.0.4
files by `tools/audit_snake_throw_lw_donor.py`); D for how it looks and how the
get-up reads on hardware.**

Two traps in a down-throw port, both of which produce a build that compiles,
audits clean, and is still the wrong move.

**1. The motion kind.** In Smash a character's four throws are `ThrowF`/`ThrowB`/
`ThrowHi`/`ThrowLw`, and they do **not** live in the same naming family as the
smashes. Snake is a live example of the collision: he has **both** a `throw_lw`
(`game_throwlw`, clip `e01throwlw.nuanmb`, cancel 48) *and* an `attack_lw4`
(`game_attacklw4`, clip `c04attacklw4.nuanmb`, cancel 56), and the second is his
**down smash**. Three independent ways to tell them apart, any one of which
suffices:

* `fighter/<donor>/ai/param/attack_data_param.prc` has an `attack_lw4` AI record
  with `cancel_frame: 56` and **no `throw_lw` record at all**. Throws are not AI
  moves.
* the smash script opens with `START_SMASH_HOLD`, `se_common_smash_start_02`,
  `rbkind_smashhold1` and `PHYSICS_START_CHARGE`, and has a `...Charge`
  follow-up clip;
* the clips differ by name family - throws are `e01throw*.nuanmb`, smashes are
  `c0Nattack*.nuanmb`.

Note also that G&W's own down throw clip is *already* called `e01throwlw.nuanmb`,
so on this recipient the file name is unchanged by the port and only the bytes
and the cancel frame move. Reading "the clip name already matches" as "nothing
changes" would ship G&W's animation under Snake's scripts.

**2. The victim's prone outcome is a collision attribute, not knockback.** Snake's
throw box is:

```text
ATTACK_ABS(THROW, 0, damage 9.0, angle 270, kbg 0, fkb 0, bkb 0, ...,
           collision_attr_lay)
```

`kbg`, `fkb` and `bkb` are **all zero**. There is no launch to copy, so reading
this as "9% plus a downward launch" is not a simplification - it is a different
move. `collision_attr_lay` routes the victim into the engine's generic
`FIGHTER_STATUS_KIND_LAY_DOWN` (`0x56`) instead of the `DAMAGE_FLY*` family, and
the victim then runs **its own** get-up. The victim's animation
(`e01thrownlw` / `e01throwndxlw`) lives under the **victim's** fighter folder in
the base game, so a throw port ships nothing victim-side and every opponent
already plays its own correct prone clip.

So a down-throw port has three parts to carry, not one:
1. the capture box (`ATTACK_ABS(..., CATCH, ...)`, which *does* carry real
   damage/angle/knockback and is not a throw);
2. the release (`ATK_HIT_ABS(..., Hash40::new("throw"), target, group, no)`,
   reading `FIGHTER_STATUS_THROW_WORK_INT_TARGET_*`) - without it the victim is
   never let go;
3. the `collision_attr_lay` attribute, which is what produces the prone outcome.

**An absent effect script is still a registration.** Snake's `ThrowLw` defines no
effect script; G&W's defines four. Omitting `effect_throwlw` from the new module
leaves the generated Default handler installed, so G&W's effects keep playing
over Snake's silent throw - and the packaged NRO still contains them, so a
name-presence audit does not catch it either. Per `04`: register an **empty**
handler at High priority to supersede the recipient's.

`ThrowLw` is a **vanilla status kind**, so a throw port allocates no custom
status id. Evidence `refs/snake_throw_lw/`, `evidence/2026-10-02_pgwr_snake_throw_lw/`.
