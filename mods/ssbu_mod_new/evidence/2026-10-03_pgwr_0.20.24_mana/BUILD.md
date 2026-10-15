# 0.20.24 Hero mana spending + attack-based recovery — build evidence (READY, NOT installed)

Date 2026-10-03. Tier B offline; **all runtime behaviour is tier D** — there is no
emulator, no console and no SD card in this workspace, so nothing below says
"works". Every hardware claim is a test the user has to run.

Package `builds/pgwr/0.20.24/`. NRO
`f365c49c91be2b0a2660fc6a60b60e28ec9a3dc1d64fb43fa4dedc86478ef381` (524 288 bytes).
Mod tree `caa466c992f5696472dfc532120bf6e49345ce8cf099f9224a672167541bdc63`
(5099 files). Baseline `builds/pgwr/0.20.23`, NRO `424914c1...`, preserved and not
installed over. No commit, no push, no emulator, no SD-card write.

## 1. Root cause of "side-B level 1 and level 2 cost no mana"

`hero_mana::address_ok` required the accessor address to satisfy
`0x100000000 <= address < 0x8000000000`.

`slot()` is the **only** gate behind side-B spending, the meter, the HUD and
recovery. On a refusal `begin_cast` returns token `0`, `try_spend` returns `true`
**without debiting**, `cast_ok` returns `true`, and the meter is never seeded.
Every one of those is the mana-off build's behaviour, so a false negative looks
like a free spell rather than like a bug — which is exactly what the user saw.

It is the only remaining possible cause, established by elimination:

* no `BattleObjectModuleAccessor` address on this title has ever been measured in
  this workspace, so the window was an unverified guess;
* `hero_side_b::state::get` performs the same category / kind / colour / entry
  reads that `slot()` performs, and makes **no** address window check;
* that lookup is *measured* working on a c06/c07 Mythra: every `ENTRY` /
  `TRANSITION` / `TARGET` / `SPAWN` line in
  `evidence/2026-10-02_pgwr_T-0052/pgwr_hero_s_log_card*_2026-10-02.txt` is
  behind it (hardware, 2026-10-02).

Fix: `address_ok` is now `address != 0 && address % alignment == 0`. Removing the
window can only admit more pointers, never fewer, so it cannot introduce a new
false positive. The same fix was applied to `hero_neutral_b::mod::address_ok`,
which gates `target()`, `entry()` and `target_weapon()`.

Tier: **B** by elimination and code reading. The runtime effect is tier D until
the user runs test 1 and 2 below.

## 2. Correction: recovery is keyed on damage **dealt**, not damage received

`hero_mana/damage.rs` previously said the donor recovers MP when "this fighter
was hit or blocked". **That was wrong**, and it is corrected in place.

The award is keyed on damage this fighter **deals** and shield damage this
fighter **takes**:

* the pinned `vl.prc` (sha256 `dafa43c6...`) names them
  `sp_recover_damage_mul` and `sp_recover_shield_mul`. A received-damage rule has
  no shield half to pair with;
* the donor's `csel` at `main+0x854a4c` selects `+0xc0` (damage) or `+0xbc`
  (shield) on one event bit, `main+0x854a60 fmul s0, s8, s0` scales a
  **damage-derived** value (`s8`, built at `main+0x8549a0..0x854a3c` with
  fighter-percentage damage scaling), and `main+0x854a68 bl 0x853890` passes the
  product to the same `add_sp` the passive recovery uses;
* `main+0x854610` has **zero `bl` callers**. It is address-taken from a vtable at
  about `main+0x3a9fc00`, so its caller — and therefore which argument is the
  attacker and which the victim — is **not recovered**. That unknown is why the
  old note guessed, and the guess was wrong.

The rule is tier B. The event ABI is unrecovered. `damage.rs` and `params.rs`
now say so.

## 3. What was built for recovery

`src/mythra/hero_mana/attack_recovery.rs`. Rule: **one award per opponent this
pair's own non-mana-costing move connects with**, amount
`AttackModule::get_power(hit_no) * RECOVER_DAMAGE_MUL`, applied through the
owned `add()` (epsilon guard, no negative, clamp to `SP_MAX`).

Trigger: a fighter-attached `CheckAttack` line callback, registered for both
halves behind the c06/c07 costume gate. That is the attacker-side "my move
connected" signal; it needs no interception and no victim-side callback, and it
reads the same collision table `hero_side_b::fighter::store_target` already reads.

Exclusions, each with a reason in the module docstring:

| exclusion | why |
|---|---|
| mana-costing casts (`NEUTRAL_SPELL` / `SIDE_SPELL`) | they already had their price debited |
| own partner and teammates (`TeamModule::team_no`) | a friendly body must not farm the meter |
| non-fighter targets | boss items and gimmicks are hit repeatedly and would stream awards |
| dead / respawning (`stock_spent`) | a stock boundary must not cross entries or matches |

Fidelity, stated honestly: the award is **proportional, not the engine's final
damage number**, because that number is not in the collision table. A
non-positive or implausible `get_power` read falls back to one passive-recovery
unit, so a misread degrades to "you still got mana for landing the hit" rather
than to a garbage award or a crash. `get_power`'s argument meanings are read off
the binding, **not measured**.

The shield half is **not built**. Observing shield damage taken requires the
victim's own collision event, and the only site that sees it is the reserved
`main+0x854610` (mod rule 17, not approved).

Tier: **D**. Never run on hardware.

## 4. Checks that ran

| check | result |
|---|---|
| `CARGO_TARGET_DIR=target cargo --offline skyline build --release --features snake-neutral-b,hero-side-b,hero-mana-hud` in `builds/.cache/mana-0.20.24/plugin` | exit 0, 0 errors |
| built from an isolated snapshot, never the shared live tree (other agents had work in flight) | yes |
| rebuild after line-ending normalisation | byte-identical NRO |
| rebuild of the **unchanged** 0.20.23 snapshot | byte-identical `424914c1...`, so the build is deterministic and byte comparison means something |
| appending a **comment only** to `hero_mana/mod.rs` | byte-identical NRO, so a hash change implies a code change |
| diagnostic build (`...,logging`) | exit 0; carries `CAST entry=`, `SPEND entry=`, `REFUSE entry=`, `RECOVER +`, `GATE-MISS`, `HIT-RECOVER` (x2), `DEBIT-SUPPRESSED`, `power=unreadable`, `attack recovery: on` |
| silent packaged NRO | all of the above markers 0 occurrences (expected: `crate::diagnostic!` compiles out) |
| packaged NRO == built NRO | yes |
| all 5099 mod files vs 0.20.23 | byte-identical except `info.toml` version |
| source delta | 1 added, 6 changed, 0 removed; `Cargo.lock`/`Cargo.toml` differ only in the version line |
| `MANIFEST.json` self-check | 8/8 pass (mod_files map, tree hash, file count, NRO hash, NRO size, every `source_files` hash, all patch files present, info.toml version) |
| all nine pinned 13.0.4 Hero mana native sites | byte-exact in `main.bin` sha256 `f70c97d2...`, re-verified directly against `refs/brave_special_n/T-0057/reserved_sites.json` |

The diagnostic build matters because the shipped NRO is silent: with
`crate::diagnostic!` compiled out, a string check cannot prove the new code is
linked. The `logging` build carries every new marker, which does.

### Byte delta is not a scope measure

0.20.23 → 0.20.24 changes 318 843 bytes in 35 001 runs spanning the whole text
section, far more than the source delta suggests. This was measured, not
assumed:

* flipping the **single** `address_ok` boolean and changing nothing else already
  changes 220 731 bytes in 30 726 runs;
* adding the `CheckAttack` registration on top adds roughly 77 k more;
* a comment-only edit and an unchanged rebuild both produce byte-identical output.

So the width is code-layout cascade, not scope creep. The scope evidence is the
source-level delta plus the 5099-file asset comparison; the NRO hash is the
identity.

## 5. Checks that could NOT run

* `tools/audit_hero_mana_hud.py`, `tools/audit_hero_side_b.py` and the other tools
  that import `main_image`/`capstone`: **no capstone wheel in this workspace** and
  nothing may be installed. These are the tools that tie each HUD constant to the
  exact instruction it was read from.
* `tools/audit_hero_mana_native.py` in full: the donor NRO `lua2cpp_brave.nro` is
  not in this workspace. The nine `main.bin` sites were re-verified directly
  instead, which covers the sites but not the tool's full report.

Neither failure changed any artifact.

## 6. Hardware tests the user must run

One state change per test. Read the **HUD gauge** — this build is silent, so there
are no log markers to grep.

1. Spawn 1v1 as Mythra c06. Do not attack. The gauge must start full and not
   drift. (It was never seeded before if `slot()` was refusing.)
2. Side-B to level 1 (Zap), release on an opponent: the gauge must drop by about
   8. Repeat for level 2 (Zapple, about 18). **This is the bug being fixed.**
3. Side-B from the air, level 1 and level 2: same expected drop. The hold path is
   shared between ground and air, so this confirms the air release path too.
4. Empty the meter, then hold side-B through the whole hold: the gauge must **not**
   refill while casting, and the move must refuse (motion plays, no sparks/bolts).
5. Jab an opponent at roughly 50 MP: the gauge must rise. Then stand still for
   5 seconds: it must rise by only the passive amount. This separates attack
   recovery from passive recovery.
6. Land a Zap that connects: the net change must be about −8 plus a small rise,
   **not** a full refund. Confirms mana-costing casts are excluded from recovery.
7. Hit a boss item or a shield without touching a fighter: the gauge must **not**
   rise. Confirms the non-fighter exclusion.
8. Take a stock: the gauge must return to full exactly once and then hold steady
   through the respawn animation.
9. Down-B swap mid-match: the gauge must show the same number on both halves (one
   meter for the pair).
10. Spot-check unchanged behaviour: Zapple bolt angle, aerial up-B gravity
    0.70/0.70, DK cargo, Incineroar back throw, Chrom jab sword.

On a crash, return the newest `sd:/atmosphere/crash_reports/` file plus the
package version and NRO hash. This build writes no mod log; existing log files
should stop receiving mod entries.

## 7. Explicitly unverified

* all runtime mana behaviour (tier D)
* whether removing the address window is in fact sufficient to make `slot()`
  accept on hardware — the fix is the only remaining candidate, not a measurement
* the magnitude of the attack-recovery award, since `get_power` is read from the
  binding rather than measured
* the donor's attacker/victim ABI at `main+0x854610`
* the shield-damage half of the donor rule: still unbuilt and still reserved

## 8. Install

Not installed; no card was mounted. When a card is present, use
`src/pgwr/install-to-card.sh` with `MGW_PACKAGE` pointing at
`builds/pgwr/0.20.24`, frameworks OFF. The manifest records
`cargo_target = "mana-0.20.24/target"`. Verify the card against `0.20.23`
independently first; the existing installer backs up, stages, compares and rolls
back.

Narrow per-file patches are in `builds/pgwr/0.20.24/patches/`, each diffed
against `builds/.cache/silent-0.20.23/plugin`.