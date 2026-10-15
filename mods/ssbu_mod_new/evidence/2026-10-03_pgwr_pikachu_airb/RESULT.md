# pikachu-airb 1.0.0 — RESULT (2026-10-03)

**Task.** Give Pyra/Mythra-as-Game-&-Watch (`eflame`) Pikachu's back air:
`AttackAirB` **and** its `LandingAirB`, gated to the modded costumes c06/c07.

**State.** READY, **not installed**. No SD-card write, no emulator run, no
console run, no commit, no branch, no push.

**Evidence tier.** B for everything in "measured" below (offline bytes,
structure, compile and binary content). **D** for everything in "not verified".
Nothing here may be described as "works".

---

## Deliverables

| what | where |
| --- | --- |
| narrow package, 19 mod files + NRO + patches + MANIFEST + BUILD.txt | `builds/pgwr/pikachu-airb-1.0.0/` |
| manifest | `builds/pgwr/pikachu-airb-1.0.0/MANIFEST.json` |
| human build/install note | `builds/pgwr/pikachu-airb-1.0.0/BUILD.txt` |
| audit JSON (128 checks) | `builds/pgwr/pikachu-airb-1.0.0/pikachu_airb_delta.json` |
| narrow source patches | `builds/pgwr/pikachu-airb-1.0.0/patches/` |
| isolated build tree | `builds/.cache/pikachu-airb/plugin/` |
| isolated **control** build (unmodified snapshot) | `builds/.cache/pikachu-airb/control/` |
| the port itself | `src/pgwr/plugin/src/acmd/pikachu_attack_air_b.rs` |
| pinned donor | `refs/pikachu_attack_air_b/` |

Key hashes:

| item | sha256 | bytes |
| --- | --- | --- |
| shipped NRO | `9d0ee7edb554d402cf31ff12dce989319804b65fece8b9cae3787e4cc3eddcee` | 524288 |
| baseline NRO (0.20.23) | `424914c18e740aea67c37ed399ffe5a22208b76f10dec81e279a8285198b777e` | 524288 |
| control rebuild of the unmodified snapshot | `424914c18e740aea67c37ed399ffe5a22208b76f10dec81e279a8285198b777e` | 524288 |
| delta tree (19 files) | `db80bba18a1b6cb21593c033a1f39442320b46a87b2f77b5bd43f3003c8f2866` | — |

Build command, copied from `builds/pgwr/0.20.23/MANIFEST.json` rather than
guessed:

```
cargo skyline build --release --features snake-neutral-b,hero-side-b,hero-mana-hud -- --offline
```

---

## Measured (tier B)

### Donor, pinned and re-checked on every run

`refs/pikachu_attack_air_b/`, extracted offline from the workspace dump
(`gamedata/ssbu-13.0.4/data.arc` via `tools/arc-extract`), plus the donor scripts
from `WuBoytH/SSBU-Dumped-Scripts` @ `59004685238a3f6f93bae905d3a4e079701c40b4`.

| motion | cancel | flags | blend | clip | game_script |
| --- | --- | --- | --- | --- | --- |
| `attack_air_b` | 300 | `0x0084` | 0 | `c05attackairb.nuanmb` | `0xf814cca56` |
| `landing_air_b` | 20 | `0x0080` | — | `c05landingairb.nuanmb` | `0x106cd2dba0` |

Clip end frames 53.0 and 30.0. Groups: Transform 55 / Visibility 38 /
Material 1 for the attack; the landing clip likewise carries a Visibility group.

### Retarget onto the built c06/c07 skeletons

165 recipient bones against 77 donor bones.

* 45 of 55 Transform nodes kept; dropped exactly `EarL1, EarL2, EarR1, EarR2,
  Hat, Have, Tail1..Tail4`.
* **0 parent-chain mismatches**, parents compared by name.
* The donor's 38-node Visibility group has **0** nodes on the recipient's idle,
  so it is rebuilt from the recipient's own idle (98 nodes). Material group (1
  node) dropped.
* All 17 tracked limb bones move. Largest `Hip` 176.6 deg, `ShoulderL` 169.1,
  `FootL` 112.7, `ShoulderR` 111.4, `HandL` 92.2, `LegR` 69.2, `FootR` 54.1,
  `LegL` 57.1, `Bust` 57.3, `KneeL` 56.5, `KneeR` 52.0, `ArmL` 50.9, `ArmR` 50.3,
  `Waist` 44.0, `HandR` 38.7. `ToeL` / `ToeR` rotate 0 deg but translate
  0.329 / 0.340 — they move by translation.
* `ElbowL` / `ElbowR` are not bones on either fighter (both carry
  `H_ElbowL/R`), so they are not in the tracked set.
* `trans`, the donor's hitbox bone, is a built-in engine anchor like `top` and
  `havel`: absent from **both** `model.nusktb` files. Used unchanged, not
  remapped. The landing writes on `top`.

### Motion list, per slot

| | `attack_air_b` | `landing_air_b` |
| --- | --- | --- |
| differing byte offsets vs 0.20.23 | `[16, 62]` — **2 bytes** | `[]` — **0 bytes** |
| cancel | 296 -> **300** | 20 (unchanged) |
| flags | `0x0080` -> **`0x0084`** | `0x0080` (unchanged) |
| entry size | preserved | preserved |
| anims | already `hash40('c05attackairb.nuanmb')` | already `hash40('c05landingairb.nuanmb')` |

No other entry in either list differs, byte for byte, over the whole file. The
landing needs no entry change because the recipient's entry is already
identical to the donor's.

### Assets and sound

* 6 tones appended per slot against **561 `se_`** and **250 `vc_`** tones
  retained: `se_pikachu_swing_s`, `se_pikachu_landing02`,
  `vc_pikachu_attack01..04`. Pre-existing sample bytes, tone records and labels
  are byte-equal after the merge; BINF/PROP/GRP/DTON/PACK identity kept.
* `eflame.sqb` gains exactly one record, byte-identical to the donor's
  `seq_pikachu_rnd_attack`. The four voice tones were **derived from that record
  by CRC32**, not hand-listed, and asserted to be exactly those four.
* `se_common_swing_02` is **not** merged: it is a common-bank swing sound.
* All three effects (`sys_spin_wind`, `sys_attack_impact`, `sys_down_smoke`) are
  common-bank `sys_*` names, so **no donor emitter is merged and no recipient
  effect bank is touched**. Asserted by the donor audit, not assumed.
* `ef_pikachu.eff` is pinned by hash but **not shipped**.

### Source

* 8 handlers ported verbatim from the pinned donor scripts and registered at
  `Priority::High` on the gated agent
  (`Agent::new("eflame").set_costume(crate::TARGET_COSTUMES.to_vec())`).
* Clean `cargo skyline build --release`, exit 0, **no new warnings** (an earlier
  revision warned on an unused constant; the claim is now carried by source
  literals the audit re-reads instead).
* No per-frame state forcing anywhere in the module (rule 19); no cleanup
  callback needed, because the move spawns no article and no long-lived effect.
* No status id consumed: both kinds are vanilla states. No `config.json` entry.

---

## Controls

Every check below is live, not decorative.

| control | expected | observed |
| --- | --- | --- |
| donor audit `--smoke` | PASS | PASS |
| donor audit, 7 negative controls (bare-stem animation hash, moved cancel, moved flags, unreadable skeleton, reparented bone, static limb chain, sequence record missing a voice child) | all caught | all caught |
| donor audit positive control (bones absent from both skeletons must not count as static limbs) | passes | passes |
| sound merge `--check` | PASS | PASS: 4 banks + `eflame.sqb` |
| sound merge on a truncated bank | preservation check fires | fired |
| sound merge repeated on its own output, tone half | **refuses** (no silent double-append) | refused |
| sound merge repeated, sequence half | byte-identical no-op | no-op |
| **unmodified snapshot rebuild, same command, same environment** | reproduces the baseline NRO | `424914c1...`, **byte identical** |
| shipped NRO rebuilt after a touch | same hash | `9d0ee7ed...` both times |
| shipped NRO line-ending change (CRLF vs LF module) | no binary change | `9d0ee7ed...` unchanged |
| NRO carries 8 handler names + 3 sound names + 3 effect names | all present | all present |
| `audit_pikachu_airb_delta.py` | 128/128 | **128/128** |
| delta audit, 8 negative controls | all caught | all caught |
| delta audit positive control (undamaged package) | passes | passes |
| delta audit, patches applied to a clean snapshot copy | reproduce the live source byte for byte | both reproduce |

Delta audit negative controls, verbatim (exit status 0):

```
PASS: motion-entry-flags-flipped: motion/c06/attack_air_b/differing-offsets: [62]
PASS: clip-truncated: clips/c05attackairb.nuanmb/identical-across-slots
PASS: voice-tone-stripped: sound/.../vc_eflame_c06/reads-back
PASS: stray-config-json: package/exact-file-set: extra=['config.json']
PASS: nro-rolled-back-to-baseline: nro/differs-from-baseline
PASS: finisher-clear-all-removed: source/one-clear-per-open-box: 2 clear_all calls, expected 3
PASS: per-frame-forcing-added: source/no-per-frame-forcing
PASS: costume-gate-removed: source/costume-gate
PASS: undamaged-package-passes: no failures

8/8 damaged inputs rejected; 1/1 undamaged input(s) accepted
```

Meta-control on the controls themselves: one damage function was temporarily
replaced with a no-op **in the real file**, the tool was run, and it had to exit
**non-zero** (`FAIL: the audit did not reject: motion-entry-flags-flipped`,
`7/8 damaged inputs rejected`); the file was then restored and its sha256
re-checked. An exit code of 0 only means something once the failure path has
been shown to fire.

### Two failures this task found in its own tooling

`build_pikachu_airb.patch_motion_list` returned the spliced `motion_list.bin`
bytes in its report and **never wrote them to disk**. The build report claimed
"cancel 296->300, 2 differing bytes" for both slots while the staged file was
byte-identical to the baseline. It was caught only because the delta audit
re-reads the packaged file from disk. Fixed in place: the function now writes,
then re-reads and compares. Written up in `handbook/05_acmd_porting.md`.

**2. The negative-control runner's exit status was inverted.** The eight
damaged-input controls all behaved correctly, but `main()` returned 1 and
printed `FAIL: 0 control(s) not caught` - nonsense on both counts. The damage
controls recorded `caught: True/False` while the positive control recorded
`caught: not ok`, i.e. the **opposite sense under the same key**, and the exit
test read the positive control's flag as if it meant "all good". So a fully
passing controls run exited non-zero. Fixed: every control now carries an
explicit `ok` plus a `kind` of `damage` or `positive`, and the summary reports
the two counts separately. Caught only because the final pass checked `$?`
instead of reading the piped output - every earlier run of this tool had been
piped through `tail`, which hides the status. **Never trust a green tail; check
the exit code.**

---

## For the mana-system agent

No mana file was read or written by this task. These are the properties of the
new back air that a mana/throw model may care about. **All measured from the
pinned donor scripts; none verified in game.**

**Hitboxes — five jabs then a finisher, 8.6% of the move.** Windows at frames
4, 8, 12, 16, 20, each two frames long then cleared (that is what makes them
five separate hits, not one long box).

| window | id | damage | angle | bkb | kbg | kbscale | standoff | offset | attr | level |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| jabs | 0 | 1.0 | 367 | 100 | 40 | 0 | 4.2 | x 3.5, y +/-4.0 | `collision_attr_rush` | S / KICK, `ATTACK_LR_CHECK_POS` |
| finisher | 0 | 3.6 | 45 | 160 | 0 | 40 | 5.0 | x 7.0, y 6.0 -> -4.0 | `collision_attr_normal` | L / KICK, `ATTACK_LR_CHECK_B` |

**Landing.** Frame 1, id 0, bone `top`, damage 4.0, angle 361, bkb 80, kbg 0,
kbscale 50, standoff 8.0, x 4.0 y 0.0, `collision_attr_normal`, level S / PUNCH,
region body; cleared at frame 3. Total 8.6% of the landing.

**Throws.** The donor's back air has **no throw**, so a mana model that expects
an air-throw on back air must special-case this move.

**Article.** None. **The G&W turtle (`normal_weapon`) no longer appears on this
move**, because the donor has no article and the generated G&W `AttackAirB` is
replaced at `Priority::High`. If the turtle is wanted back, it has to be added
deliberately; check which other moves still spawn `normal_weapon` before
changing the shared cleanup. The landing also no longer runs the generated
`normal_weapon` `change_motion("landing_air_b")` article.

**Costs.** None of the donor's sounds or effects gate on mana, and this task
adds no cost, no cooldown and no meter interaction. The only timing constant
that touches this move is `landing_attack_air_frame_b` (`params.rs` hash
`0x1a4262b54f`), left at G&W's **18.0** because Pikachu's own value is not
reachable offline.

**Reused names.** `rbkind_attackss`, `rbkind_nohits`, `rbkind_nohitm`,
`rbkind_attackm`, `rbkind_lands`, `collision_attr_rush`, `collision_attr_normal`
— all shared/common-bank, so the mana system's rumble or attr code is unaffected.

---

## Not verified (tier D)

* That the retargeted animation looks like Pikachu's back air on G&W's body.
* That the hitboxes connect with the visible arm, or that the finisher's
  `ATTACK_LR_CHECK_B` behaves as it does for Pikachu.
* That any sound or effect plays; the three effects and `se_common_swing_02` were
  never loaded by this build in any observed run.
* Whether the landing feels late at `landing_attack_air_frame_b = 18.0`.
* That the other normals, the sword, side-B, up-B, the mana HUD and the other
  five plugins are unaffected at runtime.
* Whether the removed turtle article is noticed as a regression.

---

## Console tests (one change at a time, rule 11)

Package first, then each step in a **separate boot** where noted.

1. Boot with vanilla c00 and c05. Back air must be **unchanged** G&W: turtle
   article visible, G&W hitboxes. This is the gate.
2. Boot c06. Back air from neutral: five light jabs then one hard finisher that
   launches. Watch the hitbox — it should track the visible arm, not float near
   the hip.
3. Repeat on c07. The two slots ship identical clips; any difference is a bug.
4. Jump-cancel into back air, and back air out of a short hop; confirm recovery
   is not cut short and the landing flag releases at frame 38.
5. Land on a flat platform: Pikachu's landing, `sys_down_smoke`, the landing
   sound, and **no turtle**.
6. Land on a slope and on the stage edge: the landing's slope handling and
   `rbkind_lands` rumble should read as Pikachu's.
7. Effects: spin wind at frames 2/3/12/13, impact at frame 24. Sounds: swing on
   frame 20, voice on the first hits, landing sound on the landing.
8. **Separate boot:** confirm the other normals, sword, side-B, up-B, the breath
   projectile, the mana HUD and the codex are untouched. Nothing else may have
   changed.
9. Match: play a full match and confirm no crash, no soft-lock, and the mod's
   `info.toml` still loads.
10. Boot log must show **no new lines**. 0.20.23 is the logless build, so the
    only expected output is what was already there; a new line means something
    other than this task got in.

Report back what you saw per step; anything that differs becomes a new fact
with tier A attached.