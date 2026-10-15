## Snake down throw (ThrowLw) on G&W c06/c07 — Snake down throw agent (2026-10-02)

**PENDING — NOT installed, no console run, no emulator.** Labelled by move rather
than by slot: another concurrent entry above calls itself "Freebuff slot 4".

### What this change is

Vanilla Snake's **down throw** on Pyra/G&W costumes c06 and c07, replacing G&W's
own down throw on those two costumes only. Every other move and every vanilla
costume is untouched.

ACMD: `plugin/src/acmd/snake_throw_lw.rs` (new, mine)
Assets/motion: `src/pgwr/tools/build_snake_throw_lw.py` (new, mine)
Sounds: `tools/merge_snake_throw_lw_sound.py` (new, mine)
Donor inventory: `tools/audit_snake_throw_lw_donor.py` (new, mine)
Delta audit: `tools/audit_snake_throw_lw_delta.py` (new, mine)
Pinned donor: `refs/snake_throw_lw/`
Delta package: `builds/pgwr/snake-throw-lw-delta/`
Record: `evidence/2026-10-02_pgwr_snake_throw_lw/RESULT.md`

### The move kind is `throw_lw`, NOT `AttackLw4`

Worth stating loudly, because the two differ by one word and **both exist in
Snake**. `AttackLw4` is the **down smash**. Three measurements settle it:

| kind | game script | clip | cancel |
|---|---|---|---|
| `throw_lw` | `game_throwlw` | `e01throwlw.nuanmb` | 48 |
| `attack_lw4` | `game_attacklw4` | `c04attacklw4.nuanmb` | 56 |

1. Snake's `attack_data_param.prc` has an `attack_lw4` AI record at
   `cancel_frame: 56` and **no** `throw_lw` record at all.
2. `game_attacklw4` opens with `START_SMASH_HOLD`, `se_common_smash_start_02`,
   `rbkind_smashhold1` and `PHYSICS_START_CHARGE`, with an `AttackLw4Charge`
   follow-up clip. Those are down-smash marks.
3. `AttackLw4.txt` / `AttackLw4Charge.txt` are pinned at the same commit purely
   as the control. The audit asserts `throw_lw` and `attack_lw4` never name the
   same game script, so a future revision that merged them would be caught.

`refs/snake_throw_lw/donor_acmd/` holds all three, sha256 in `manifest.json`.

### The victim's prone outcome is `collision_attr_lay`, not knockback

The donor's throw box reads damage 9.0, angle 270, with **kbg, fkb and bkb all
zero**. There is no launch to copy, so "damage plus a downward launch" would be a
*different move*, not a simplification. `collision_attr_lay` routes the victim
into the engine's generic `FIGHTER_STATUS_KIND_LAY_DOWN` (0x56) rather than the
`DAMAGE_FLY*` family, and the victim then runs its own get-up.

Concretely, all three parts of capture/release are carried verbatim:

1. the capture box — `ATTACK_ABS(..., CATCH, 0, 2.0, 361, 100, 0, 60, ...)`,
   `ATTACK_LR_CHECK_B`;
2. the release — `ATK_HIT_ABS(THROW, Hash40::new("throw"), target, group, no)` at
   frame 35, reading the three `FIGHTER_STATUS_THROW_WORK_INT_TARGET_*` ids;
3. the `collision_attr_lay` attribute on the throw box.

Nothing victim-side ships: `e01thrownlw` / `e01throwndxlw` live under the
*victim's* own fighter folder in the base game, so every opponent already plays
its own correct prone clip.

### Measured delta (tier B) — overlay on 0.20.19, 10 files

Delta root: `builds/pgwr/snake-throw-lw-delta/ultimate/mods/pyra_gamewatch_reskin`
MANIFEST: `builds/pgwr/snake-throw-lw-delta/MANIFEST.json`
(`2150b01bc3b6bb416adaf4b85e2456a6dfe0f4a89f442929def9c338f6626881`)

| file | delta sha256 |
|---|---|
| `fighter/eflame/motion/body/c06/e01throwlw.nuanmb` | `28381e8bc06e410b4c44583564eb362bb202b5add948dd04acd42e47127d79da` |
| `fighter/eflame/motion/body/c07/e01throwlw.nuanmb` | `28381e8bc06e410b4c44583564eb362bb202b5add948dd04acd42e47127d79da` |
| `fighter/eflame/motion/body/c06/motion_list.bin` | `524d8fc95e0a6396dec54e4b2468acc07ac97ff6ce162bd7f3c2466acd4277a0` |
| `fighter/eflame/motion/body/c07/motion_list.bin` | `524d8fc95e0a6396dec54e4b2468acc07ac97ff6ce162bd7f3c2466acd4277a0` |
| `sound/bank/fighter/se_eflame_c06.nus3audio` | `12bbc3f14d3ce2d3b3e6353f6d8b3252cd28e6f10010eae441cf109341963a85` |
| `sound/bank/fighter/se_eflame_c06.nus3bank` | `c81848142bbfb8e10b6e79ec77f4b5ca302d88731ce9012a11c7cb679a787444` |
| `sound/bank/fighter/se_eflame_c06.tonelabel` | `f961410ded27222bceae17871986fa64254150c529203f964d3e721306675adb` |
| `sound/bank/fighter/se_eflame_c07.nus3audio` | `12bbc3f14d3ce2d3b3e6353f6d8b3252cd28e6f10010eae441cf109341963a85` |
| `sound/bank/fighter/se_eflame_c07.nus3bank` | `c81848142bbfb8e10b6e79ec77f4b5ca302d88731ce9012a11c7cb679a787444` |
| `sound/bank/fighter/se_eflame_c07.tonelabel` | `f961410ded27222bceae17871986fa64254150c529203f964d3e721306675adb` |

* `throw_lw` is the **only** changed entry of **841**, per slot. Cancel
  **50 -> 48**, flags `0x80` unchanged, **file size preserved** (both entries are
  28 bytes, so a pure in-place splice). The tool asserts every other entry is
  byte-identical.
* `attack_lw4` (down smash) cancel still **34**, asserted untouched.
* Clip: **77 of 87** transform nodes kept; the 10 dropped are `FaceN` and the
  nine `S_Bandanna*`; 0 case-only matches; **every limb bone measured moving**
  against the recipient idle (`deploy_for_slot` refuses a static limb).
* Sound: **544** tones retained byte-for-byte per slot, **4** appended.
* No new clip file names, therefore **no `config.json` change**. No c00-c05 file,
  no Mythra file, no `status/mod.rs` edit, **no shared version bump**.

### Four tones ship, not the two the script names

`se_snake_catch_tight` is the **only kind-1 (sequence) tone among the 111** in
`se_snake_c00`, and it references `se_snake_catch_tight_01` and
`se_snake_catch_tight_01_layer` by **bank-relative index 92/93**. Those are
rebased to 545/546. The shared codec's `group_links` decodes donor tone kinds 0
and 3 and asserts on others, and correctly refused; appending only the two named
tones would have left the grab sound pointing at two unrelated tones already at
index 92/93 in Pyra's 544-tone bank, with every byte-level check still passing.
Two negative controls back this (truncated bank; unrebased donor index).

No `PLAY_SEQUENCE` is played, so **`eflame.sqb` is deliberately not written**.

### An empty `effect_throwlw` is registered on purpose

Snake's `ThrowLw` defines no effect script; G&W's defines four
(`sys_smash_flash_s` at 1 and 22, `sys_down_smoke` at 21, `sys_landing_smoke` at
35). Simply omitting the handler would leave the generated Default one installed
and G&W's effects playing over Snake's silent throw. Per `handbook/04` ("port
what the donor has, empty what only the recipient has") an empty handler is
registered at High priority. Found by inspecting the built NRO, not by reading
the donor.

### Shared-file dependency

`src/pgwr/plugin/src/acmd/mod.rs` — three narrow hunks, already applied to the
working tree; an unapplied copy is kept at
`refs/snake_throw_lw/integration/0001-acmd-mod-add-snake_throw_lw.patch` for
re-application if another agent's edit to the same file conflicts:

1. `pub mod snake_throw_lw;`
2. the `table::THROW_LW` description line
3. `snake_throw_lw::install();` after `snake_attack_hi3::install();`

**No conflict with the other three concurrent tasks is expected:** they work on
Mythra (`mythra/mod.rs`) or on `gaogaen_throw_b` in `acmd/`. The one shared
surface is `acmd/mod.rs`.

### Status ids requested

**None.** `ThrowLw` is a vanilla status kind entered from the grab, so this move
allocates nothing. **Next free Pyra id remains `0x208`** (unchanged).

### Installer: exactly what to run

    # from the mod repo root, D = the delta overlay, T = your merged tree
    D=builds/pgwr/snake-throw-lw-delta/ultimate/mods/pyra_gamewatch_reskin
    T=builds/pgwr/<your-version>/ultimate/mods/pyra_gamewatch_reskin
    for f in fighter/eflame/motion/body/c06/e01throwlw.nuanmb \
             fighter/eflame/motion/body/c07/e01throwlw.nuanmb \
             fighter/eflame/motion/body/c06/motion_list.bin \
             fighter/eflame/motion/body/c07/motion_list.bin \
             sound/bank/fighter/se_eflame_c06.nus3audio \
             sound/bank/fighter/se_eflame_c06.nus3bank \
             sound/bank/fighter/se_eflame_c06.tonelabel \
             sound/bank/fighter/se_eflame_c07.nus3audio \
             sound/bank/fighter/se_eflame_c07.nus3bank \
             sound/bank/fighter/se_eflame_c07.tonelabel ; do
      cp "$D/$f" "$T/$f"
    done

    # re-derive the same delta from scratch instead (equivalent, reproducible):
    python src/pgwr/tools/build_snake_throw_lw.py \
      --baseline builds/pgwr/0.20.19/ultimate/mods/pyra_gamewatch_reskin --out "$D"
    python tools/merge_snake_throw_lw_sound.py --check
    python tools/merge_snake_throw_lw_sound.py \
      --baseline builds/pgwr/0.20.19/ultimate/mods/pyra_gamewatch_reskin --output "$D"

    # verify after copying
    python tools/audit_snake_throw_lw_delta.py --baseline "$T" --delta "$D"

If your merged tree already carries another agent's motion-list or bank edits,
run the two generators against **your** tree instead of 0.20.19 and re-run the
audit; both are append-only and refuse a baseline they were not measured on.

**Do not reuse this task's NRO.** `ed9a790e7c8ab690ad6d38ad564cb99d47dfb1a8b18e873fc9395c066a4d1185`
(471,040 B) is a *verification* artifact built from a copy of the crate in which
the three in-flight modules were commented out, because
`src/mythra/ness_throw_b.rs` does not compile (unresolved crate `singletons`).
Rebuild from the merged source.

### Manual console test (12 steps, vanilla control included)

1. Boot fresh and keep `sd:/ultimate/pgwr_log.txt` **from boot**.
2. **Vanilla control.** Pick Pyra c00. Grab an opponent and press down+attack.
   Down throw must behave exactly as before (G&W's), with the G&W throw flash and
   smoke effects. This is the negative control for the costume gate.
3. Also confirm Mythra c00's down throw is unchanged (it is a different fighter
   and must be untouched).
4. Pick **Pyra c06**. Grab an opponent and press down+attack. Expect Snake's
   animation, 9% damage, **no flash/smoke effects**, and Snake's grab and throw
   sounds.
5. Judge the release: the victim must be **let go**, and must go **down prone on
   the ground and then get up** — not launched upward and not launched hard along
   the floor. Report which of those three you actually see.
6. Compare with **stock Snake** as the donor control: same damage, same prone
   outcome, same get-up.
7. Pick **Pyra c07** and repeat step 5.
8. **Vanilla-costume control.** Pyra c01-c05 must still show G&W's down throw with
   its effects.
9. Confirm **the down smash is untouched**: on c06/c07, down+attack *without* a
   grab must still be G&W's down smash with its own effects and sound.
10. Confirm the other throws are untouched on c06/c07: forward, back and up throw
    must still be G&W's, with G&W's effects.
11. Watch for the **known risk**: if the victim is never released, or the game
    stalls at the throw, report it immediately and stop — that is the `throw`
    bone, which is not on the built c06/c07 skeleton. Do not keep retrying.
12. Return the boot log and, on any crash, the new file in
    `sd:/atmosphere/crash_reports/`.

**Pass / fail markers.** With `logging` off there are no `[PGWR-*]` lines for this
move and none are expected. Pass = steps 4-7 behave like stock Snake, steps 2, 3,
8, 9 and 10 are unchanged. Fail = any of: the victim is never released; the game
stalls or crashes in the throw; c00-c05 changed; the down smash changed; the
other three throws changed; G&W's throw effects still play on c06/c07; or the
grab sound plays but is audibly the wrong/layered sample.

### Blockers

- **None for the port itself.** It is source-complete, packaged and audited.
- Blocked for *installation* only by the shared build: the tree does not compile
  while `src/mythra/ness_throw_b.rs` is in flight. Whoever owns that file must
  resolve the `singletons` import.
- Runtime behaviour is **tier D** until step 12 comes back. Nothing in this
  section has been run on hardware, on Ryujinx, or in any automated test.