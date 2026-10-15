# Snake down throw (`ThrowLw`) on pgwr G&W c06/c07 — 2026-10-02

**Freebuff slot 4. Evidence tier B (offline). No console, no emulator, no card
access, no automated gameplay test. Every runtime statement below is tier D.**

Manifest: `builds/pgwr/snake-throw-lw-delta/MANIFEST.json` (`2150b01bc3b6bb4...`).

## What was ported

Snake's vanilla **down throw** on Pyra/G&W costumes c06 and c07 only, replacing
G&W's own down throw there. Script
`plugin/src/acmd/snake_throw_lw.rs`, asset builder
`src/pgwr/tools/build_snake_throw_lw.py`, sound delta
`tools/merge_snake_throw_lw_sound.py`, audit `tools/audit_snake_throw_lw_delta.py`.

## The move identity is `throw_lw`, not `AttackLw4` — verified (B)

This is the single most dangerous thing to get wrong here, because the two names
differ by one word and **both exist in Snake's base game**. Measured by
`tools/audit_snake_throw_lw_donor.py` (`refs/snake_throw_lw/inventory.json`):

| kind | game script | clip | cancel | what it is |
|---|---|---|---|---|
| `throw_lw` | `game_throwlw` | `e01throwlw.nuanmb` | 48 | **the down throw** |
| `attack_lw4` | `game_attacklw4` | `c04attacklw4.nuanmb` | 56 | the **down smash** |

Three independent confirmations that `attack_lw4` is the smash:
`attack_data_param.prc` carries an `attack_lw4` AI record at `cancel_frame: 56`
and **no** `throw_lw` record; `game_attacklw4` opens with `START_SMASH_HOLD`,
`se_common_smash_start_02`, `rbkind_smashhold1` and `PHYSICS_START_CHARGE`; and
an `AttackLw4Charge` follow-up clip exists. `AttackLw4.txt` and
`AttackLw4Charge.txt` are pinned at the same commit purely as the control.

The audit carries a negative control asserting `throw_lw` and `attack_lw4` name
different game scripts, so a future revision that merged them would be caught.

## The victim's outcome is not "damage plus a downward launch" — measured (B)

The donor's numbers look like a mistake if you assume they are knockback:

```
ATTACK_ABS(THROW, 0, damage 9.0, angle 270, kbg 0, fkb 0, bkb 0, ...,
           collision_attr_lay)
```

**`kbg`, `fkb` and `bkb` are all zero.** There is no knockback to copy, so the
numbers alone cannot produce the move's behaviour. The prone outcome comes from
`collision_attr_lay`, which routes the victim into the engine's generic
`FIGHTER_STATUS_KIND_LAY_DOWN` (`0x56`, pinned `lua_const.rs`) rather than the
`DAMAGE_FLY*` family; the victim then runs its own get-up. The victim's
animation is its own — `e01thrownlw` / `e01throwndxlw` live under the *victim's*
folder in the base game, which is why nothing victim-side is shipped here.

All three pieces of capture/release are carried verbatim: the CATCH box
(damage 2.0, angle 361, kbg 100, fkb 60, `ATTACK_LR_CHECK_B`), the release
(`ATK_HIT_ABS` on bone `throw` at frame 35, reading the three
`FIGHTER_STATUS_THROW_WORK_INT_TARGET_*` ids), and the lay attribute.

## The grab sound is a sequence tone — measured (B), and it nearly went wrong

`se_snake_catch_tight` is the **only kind-1 (sequence) tone among the 111 tones**
of `se_snake_c00`, and it references `se_snake_catch_tight_01` and
`se_snake_catch_tight_01_layer` by **bank-relative index 92 / 93**.

The shared codec `merge_hero_neutral_b_sound.group_links` decodes donor tone
kinds 0 and 3 and *asserts* on anything else — correctly. It refused here, which
is why this was caught. Had the assertion been looser, appending the two named
tones alone would have produced a byte-consistent bank in which the grab sound
points at two unrelated tones already living at index 92/93 in Pyra's 544-tone
bank. `merge_snake_throw_lw_sound.py` therefore appends the **transitive
closure — four tones** — and rebases 92→545 and 93→546, then resolves every
rebased link back to its name in the written bank.

Two negative controls back this: a truncated bank must fail preservation, and a
bank with the *donor* index restored must fail the link check.

## The generated G&W effect script had to be superseded explicitly

Snake's `ThrowLw` defines **no effect script**; G&W's defines four
(`sys_smash_flash_s` at frames 1 and 22, `sys_down_smoke` at 21,
`sys_landing_smoke` at 35). Omitting `effect_throwlw` from the new module would
have left the generated Default handler installed, so G&W's effects kept playing
over Snake's silent throw — and the NRO would still have contained them. Per
`handbook/04` ("port what the donor has, empty what only the recipient has") an
**empty** `effect_throwlw` is registered at High priority. This was found by
inspecting the built NRO, not by reading the donor.

## Measured deltas (tier B)

* Motion list: `throw_lw` is the **only** changed entry of **841**, per slot.
  Cancel 50 → 48, flags `0x80` unchanged, file size preserved (both entries are
  28 bytes, so it is a pure in-place splice).
* `attack_lw4` (down smash) cancel still 34 — deliberately untouched.
* Clip: 77 of 87 transform nodes kept, 10 dropped (`FaceN` + nine
  `S_Bandanna*`), **all limbs measured moving** against the recipient idle.
  Node coverage alone cannot see a static pose — the R.O.B. down-tilt failure
  the user already rejected — so `deploy_for_slot` refuses a static limb.
* Sound: 544 tones retained byte-for-byte per slot, 4 appended.
* No new clip file names, so **no `config.json` change**. No c00-c05 file. No
  Mythra file. No `status/mod.rs` change. No version bump.

## Files

New: `plugin/src/acmd/snake_throw_lw.rs`,
`src/pgwr/tools/build_snake_throw_lw.py`,
`tools/merge_snake_throw_lw_sound.py`,
`tools/audit_snake_throw_lw_delta.py`,
`tools/audit_snake_throw_lw_donor.py`, `refs/snake_throw_lw/**`.

Shared, edited narrowly: `plugin/src/acmd/mod.rs` (three hunks; unapplied copy
in `refs/snake_throw_lw/integration/0001-acmd-mod-add-snake_throw_lw.patch`).

## Not established (tier D until the user tests)

How the move looks; whether the victim is actually released (the `throw` anchor
is not on the built skeleton, as it is not for G&W's own down throw); whether the
victim visibly lies prone and how long the get-up takes; whether the two Snake
tones play; whether the four G&W effects are indeed silent.

## Build caveat

`src/mythra/ness_throw_b.rs` (another agent, in flight) does not compile —
unresolved crate `singletons`. The tree therefore does not build as a whole. My
module was compiled and its NRO inspected in a **copy** of the crate
(`builds/.cache/snake-throw-lw-crate`) with the three in-flight modules commented
out; nothing in the real tree was altered. **That NRO is a verification artifact,
not a shippable binary.**