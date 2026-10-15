# Console test — 2026-10-03 — gaogaen_throw_b 0.3.0 installed over 0.20.20

Fill in the verdict next to each step and return this file. Nothing below is a pass until you say so.

**On the card:** NRO `5d7d9b8e565d9b38d6a73d804a36f4028e6fcd80ff92f15739ed96f3b783689b`,
mod tree `7a33ab21e5a6c313b20c7c6160d4b7cf92914bf759a45be11a5c4364e50bae2c` (1992 files).
Backup of the previous state: `evidence/sd-backups/sd-backup-20261003-021215`.

`logging` is OFF, so there are no `[PGWR-*]` lines. The move has its own log:
**`sd:/ultimate/pgwr_gaogaen_throw_b_log.txt`** — please return it **from boot**.

---

## 1. Boot check

Boot the game normally. Open `sd:/ultimate/pgwr_gaogaen_throw_b_log.txt`.

- **Pass** if it contains a `REGISTERED status=0x208` line for eflame naming costumes c06/c07.
- **Fail** if it contains `DISABLED common NRO callback unavailable`, or if the file does not exist
  at all. Stop and report; nothing else can be judged without registration.

Also note whether any new file appeared in `sd:/atmosphere/crash_reports/`.

## 2. Vanilla controls — do these first

Negative control for the costume gate. **None of these may change.**

- **2a.** Pyra **c00**: grab and back-throw. Must be stock G&W — its own animation, effects, sound.
- **2b.** Pyra **c01-c05**: same. All five must look identical to c00.
- **2c.** Native **Incineroar**, unboosted, same stage and victim: this is the **donor control**. Note
  its damage, launch angle and distance for steps 5-7.

## 3. Pyra c06 — the new move

Grab an opponent, then back-throw (grab while holding back). Expect **Incineroar's** animation and
sounds on a G&W body, not G&W's throw.

- Report whether the animation reads correctly or looks wrong (stretched limbs, sliding feet,
  floating).

## 4. Facing, both directions

Throw facing right, then facing left.

- The move is documented to **not** carry `REVERSE_LR`. Report whether your character turns around
  in each direction. This is a deliberate donor difference, not automatically a bug — say what you
  see.

## 5. Damage and launch

Compare against the native Incineroar from step 2c and against stock G&W.

- Report the percentage it deals against a stock 100 % target, and how far the victim flies.
  The donor is noticeably harder and more sideways than G&W's back throw; if it behaves exactly
  like G&W's, the ACMD registration did not take.

## 6. Victim sizes

Throw a small (Pichu), a medium (Sheik) and a large (Bowser) victim.

- All three must be caught and thrown. None may pass through, snap free, or launch wildly
  differently. Report any T-pose, stretched limb or hovering victim.

## 7. Timing

Frame-step if you can: **hit 28, clear 29, release 30**; cancel/recovery around **frame 52**.

- Throw a still opponent: they must be held, then released on the donor's beat.
- Confirm you can act again after the move ends.

## 8. Third fighter nearby — no invented hitbox

The donor's back-throw impact is **catch-only**: it has no collateral hitbox. Stand a third
fighter next to the throw.

- Report whether they get hit. Being hit would mean a box was invented; not being hit is correct.

## 9. Effects, camera and sound

Expect: camera **(-4, 5)**, smoke at frame **22**, a crown effect at frame **28**, rumble/quake, and
**six sound/voice cues** from the donor.

- Report which of these you actually see and hear. A silent throw, or G&W's own throw effects, means
  the effect or sound merge did not land.
- Also test an ordinary (non-KO) throw and a KO throw.

## 10. Interruption and cleanup

Interrupt the throw before, during and after impact where the rules allow it. Test at a platform
edge and a ledge. Then KO someone and start a rematch.

- After each: no leftover links, no stuck attack, no invincibility, no stuck camera, no held item
  visible, no T-pose.

## 11. Revenge control

Repeat step 3 with **Revenge active**.

- The recipient is intended to stay on the **unboosted** path. It must **not** gain a Revenge
  multiplier or any Revenge state. Report any boost.

## 12. Regression — the previously shipped moves

These are also on the card and also untested. Confirm none of them changed:

- **12a.** G&W **c06/c07 down throw** (Snake's): snake animation, no G&W throw flash/smoke.
- **12b.** Mythra **c06/c07 back throw** (Ness's): Ness animation, PSI rushing toward the grab.
- **12c.** Mythra **c06/c07 down smash** (Lucas's).
- **12d.** A few ordinary moves on c06 and c07: jab, forward smash, neutral-B.

Report any move that behaves differently from before this install.

## 13. Return

- `sd:/ultimate/pgwr_gaogaen_throw_b_log.txt`, **from boot**.
- Any new file in `sd:/atmosphere/crash_reports/`.
- Your verdict per step.

### Pass / fail summary

**Pass** = step 1 registers `0x208`; steps 3-7 behave like real Incineroar; steps 2, 8, 11, 12 are
unchanged; no crash, stall or freeze.

**Fail** = any of: no `REGISTERED status=0x208` or a `DISABLED` line; c00-c05 changed; the throw
behaves like vanilla G&W's (registration did not take); the victim is never released; T-pose or
stretched limbs; the third fighter is hit; a previous move changed; the game stalls or crashes
mid-throw.

`ENTER` / `VICTIM_INIT` / `END` lines in the log prove the code path **executed**. They are not
evidence that the move feels right — only your eyes settle that.

### If it is worse than before

If the game stalls or crashes where it did not before, say so and stop. Say which step. The previous
state is restorable from `evidence/sd-backups/sd-backup-20261003-021215`.
