# T-0060 - Lucas down smash on Mythra c06/c07

2026-10-02, Freebuff slot 4 (Buffy). **PENDING - not installed, no console run.**

Immutable record of one development session. What follows is what was measured
offline; none of it is a claim about behaviour in game.

## What was built

Vanilla Lucas's complete down-smash family on **Mythra** (`elight`) c06/c07,
replacing stock Mythra's down smash on those two costumes only. All seven of the
donor's own ACMD scripts, his own animation and motion metadata, his own hitbox
frame data, his own effects and his own sounds.

| piece | source | where it lives in the package |
|---|---|---|
| 7 ACMD scripts | `refs/lucas_attack_lw4/donor_acmd/lucas__AttackLw4.txt`, `...Charge.txt` | `src/pgwr/plugin/src/mythra/lucas_attack_lw4.rs` |
| `c04attacklw4.nuanmb` (74 frames) | Lucas c00, retargeted | `fighter/elight/motion/body/c0{6,7}/` |
| `c04attacklw4charge.nuanmb` (61 frames) | Lucas c00, retargeted | `fighter/elight/motion/body/c0{6,7}/` |
| `attack_lw4` cancel **316** (was 56) | Lucas's own motion entry | `motion_list.bin`, 2 bytes |
| `LUCAS_PSI_HOLD`, `LUCAS_PSI_ATK_LW` | Lucas's own bank, merged | `ef_elight_c0{6,7}.eff` |
| 5 SE + 1 VC tone | Lucas's own banks, merged | `se_elight_c0{6,7}.*`, `vc_elight_c0{6,7}.*` |

## Frame data, read off the donor scripts (not from a guide)

Three hits on `top`, all `collision_attr_elec` / `ATTACK_REGION_PSI`, all
`ATTACK_SETOFF_KIND_OFF`:

| frame | damage | knockback | window | offset | shake | extra |
|---|---|---|---|---|---|---|
| 20 | 17 | 43 | 8 | (2.5, 8.0) | -10 | `set_target_category(0, NO_IF)` at 23 |
| 29 | 14 | 30 | 9 | (3.3, 8.5) | -8 | `set_target_category(0, NO_IF)` at 32 |
| 39 | 11 | 20 | 9 | (-5.6, 8.0) | -6 | cleared at 42 |

`set_target_category(0, COLLISION_CATEGORY_MASK_NO_IF)` after the first two is
what stops one sweep re-hitting the same target, and it is the reason the three
frames are three separate ATTACK calls rather than one box.

Charge hold (61 frames): `physics!(START_CHARGE, 0.9, 0.6, -1, 0.1, 0.05, -1)`,
`AREA_WIND_2ND_arg10(0, 1, 220, 3, 0.2, -7, 5, 14, 10, 80)`,
`rbkind_smashhold1` at 0 and `rbkind_smashhold2` at 61. Release swing:
`AREA_WIND_2ND_RAD_arg9(1, 0.1, 0.2, 3, 0.2, 9, 4, 18, 80)` at frame 20, erased at
45. `rbkind_beams` at 19, 29, 39. Item hidden at 0, back at 62.

## Three findings that would each have produced a wrong port

**1. The charge hold is `attack_lw4_hold`, not `attack_lw4_charge`.** A first
pass looked for `attack_lw4_charge`, found nothing, and read as a missing donor
file. `hash40('attack_lw4_hold')` is `0xfee188235` and that is what the donor's own
entry carries. The kind and the script name are also not a mechanical pair: kind
`attack_lw4_hold`, script `game_attacklw4charge`. Proven by re-parsing **G&W's**
motion list and comparing every field against
`dumps/scripts/gamewatch_motion_list.yml` - an independent dump of a different
fighter's list by different tooling. G&W `attack_lw4` reads cancel 34, flags 0x80,
`game_attacklw4`, `c04attacklw4.nuanmb`, exactly as the yml says.

**2. `havel` is not a bone on either fighter.** The charging orb is parented on
`havel`. Measured: neither Mythra's nor Lucas's own `model.nusktb` contains a
bone of that name, and neither contains `top`, `haver` or `sword1` either. These
are the engine's built-in anchors. So the donor's anchors are used unchanged.
Remapping to `HandL` would have been guessing whether a retarget was needed at
all - and the same question is why every hitbox in this game is written on `top`
and works.

**3. The motion-list delta is two bytes, and the hold needs none at all.** Lucas
`attack_lw4` is cancel **316** against Mythra's 56; the two entry bodies differ at
byte offsets **[62, 63]** and nowhere else. `attack_lw4_hold` is **byte-identical**
between the two fighters. So this port changes one u16 in one entry, and
`tools/apply_lucas_downsmash_motion_list.py` re-parses its own output to prove
nothing else moved.

## Retargeting: name filter, and the parent check that a name filter cannot do

66 of 68 transform nodes survive on the Mythra skeleton. The 2 dropped are `Bat`
and `BatL` - his bat - which is why the move needs no article. 0 case-only
matches. **0 parent mismatches**: parent chains are compared *by name* between
the two skeletons, because a bone that survives under a different parent bends the
wrong way and a plain name filter cannot see that.

The donor's Visibility group names 28 of his own face/eye meshes, none of which
exist on Mythra, so the group is replaced with the **recipient's own idle**
visibility states, read from the built `a00wait1.nuanmb` beside the output. The
donor has **no Material group** at all.

All 17 real limb bones are present and measurably moving - this is the R.O.B. down
tilt lesson, where a retarget left limbs in rest pose and the user rejected it:

`LegL/R` 127.1/128.7 deg - `KneeL/R` 102.6/102.4 - `FootL/R` 60.8/62.8 -
`ClavicleL/R` 125.3/97.4 - `ShoulderL/R` 122.4/138.7 - `ArmL/R` 105.9/86.2 -
`HandL/R` 100.0/107.8 - `Hip` 66.1 deg. The charge hold moves the same 17.

An earlier draft of the measurement listed `ElbowL/R` and `WaistL/R`, which are
**not bones on either fighter** (the forearm helpers are `H_ElbowL/R`, the pelvis
is plain `Waist`). They reported as static limbs forever. A gate that counts
absent bones as static limbs is a gate that cries wolf, so the list is real bones
only.

## Assets: recipient-owned, not donor folders

`kb/findings/effect-ownership-of-donor-banks-and-per-slot-trails.md` measured that
an `.eff` under `effect/fighter/lucas/` is loaded by **nobody** - a fighter only
reaches its own per-slot bank. Shipping a copy of `ef_lucas.eff` would add 10.6 MB
that never loads while every offline check still passed. So:

* **Effects** merged into the recipient-owned `ef_elight_c06.eff` (128 -> 130
  emitters, 0 lost) and `ef_elight_c07.eff`, which the shipped `config.json`
  already declares. **0 texture and 0 model ids relocated** - the two sets share
  no id with a different payload. The relocation machinery is there anyway: the
  T-0050 write-up records a merge that relocated textures but silently collided
  on a model id, so `AddPrimitive` dropped it and the donor's arc would have drawn
  Mythra's mesh while every check passed.
* **Sounds** appended to Mythra's own c06/c07 banks. All **389** SE and **233** VC
  baseline tones per slot preserved byte-for-byte and in order, with labels
  intact; **+5 SE** (`se_lucas_smash_l01..l04`, `se_lucas_pk_charge`) and **+1 VC**
  (`vc_lucas_attack07`). All six are single-sample tones, asserted - a group tone
  would carry child indices into the recipient's list and play the wrong sample.
* `se_common_smash_start_04` is the seventh name the move plays and needs no
  merge: it is common-bank. Measured, not assumed.
* **No `config.json` change.** Both clip names already exist in the base game at
  the same ARC path, and the effect banks are already declared. The audit asserts
  this against `dumps/decoded/arc_files.tsv` rather than trusting the file list.
* **No new status id.** `attack_lw4` and `attack_lw4_hold` are vanilla status
  kinds. Mythra's own table (Hero's Spin `0x1F1..0x1F4`) is untouched, and the
  next free id is unchanged.
* **No sequence record.** The donor's down smash plays no `PLAY_SEQUENCE`, read
  out of both pinned scripts, so `elight.sqb` needs no append.
* **No c00-c05 file is touched**, asserted by scanning the package.

## The one conversion error in the donor text

`expression_attacklw4` at frame 6 reads:

```text
WorkModule::is_flag(agent.module_accessor, *FIGHTER_STATUS_ATTACK_FLAG_SMASH_SMASH_HOLD_TO_ATTACK);
if(methodlib::L2CValue::operator==(lib::L2CValueconst&)const(false, true)){
```

That is the dump losing a `== false`. Resolved as
`if WorkModule::is_flag(...) {` - the reading `acmd::littlemac_attack_s4` already
ships and the user **hardware-confirmed on 0.20.14**, and Little Mac's own
`AttackS4.txt` at the same pinned commit contains the identical broken pair. So
it is a known artifact of the dump, not of this donor.

## Deliberately not carried over

Vanilla Mythra's down smash opens and closes her sword article around the move.
Lucas has no sword, so his does not, and that asymmetry is kept - the same call
`mythra::throw_lw` makes. Opening her blade would put her own sword animation
back on top of a donor move that is not a sword move.

## Offline checks (all passed; none of them behavioural)

* Donor pins verified, and the entry parser cross-validated against G&W's
  independent dump.
* Release compile clean in `builds/.cache/pgwr-fb-4-lucas-downsmash-target`,
  features `snake-neutral-b,hero-side-b`, `logging` off. **No new warnings**; the
  only warnings are pre-existing ones in other modules.
* Packaged NRO `b51dcb278e444e864a50729a764115725ef927bc905a01a6f1b1e34402898160`
  (475,136 B) carries all 21 checked markers: 7 handler names, the log prefix,
  `elight`, 6 sound names, 2 effect names, 3 rumble names, `collision_attr_elec`.
* Clips re-read after saving: node set, group list and final frame all verified
  against the in-memory result.
* Sound merge: pins, script-coverage exactness, donor tone presence, recipient
  cleanliness, and a **negative control** that a deliberately damaged
  pre-existing tone is rejected.
* Effect merge: donor bank pinned, script coverage exact, and the merge tool's own
  decoded-field and opaque-subsection equality checks on re-export.
* Delta audit vs the installed 0.20.19 baseline: **16 overrides + 4
  vanilla-path clip overrides, 0 removed, 0 unrequested, no new file name**, with
  all 759 motion entries checked and only `attack_lw4` changed, and **three
  negative controls firing** (baseline cancel is 56 not 316; a damaged motion list
  is rejected; baseline banks carry no Lucas tones).

### One self-inflicted audit bug worth recording

The effect name reader's regex left the NUL terminator outside the capture group,
so it truncated the last character of every name and read `LUCAS_PSI_HOL`. That
presented as "the merge added a different emitter" - a failure pointing at the
package when the fault was in the audit. The reader now self-tests against the
donor bank before it is used, and a truncating reader fails that test.

## Baseline and delta

Baseline is the **installed 0.20.19** card tree, not vanilla: it carries the 25
Hero neutral-B/side-B motion entries, so Mythra's motion lists are 759 entries and
a vanilla comparison would report changes this task did not make.

```
mod tree  f8666b2494f444809a7284bfc0d0e9e694620a6ea8ff837d0a5d1b4851e9fdc6  (24 files)
motion    attack_lw4 cancel 56 -> 316, bytes [5526, 5527] of the entry at [5464, 5528)
          attack_lw4_hold byte-identical; all 758 other entries byte-identical
clips     c04attacklw4.nuanmb        9990ed0710101aac...  (48280 B, 66 nodes, 74 frames)
          c04attacklw4charge.nuanmb  362a99d29fd3ad0a...  (25641 B, 66 nodes, 61 frames)
          byte-identical across c06 and c07 (measured, asserted)
effects   ef_elight_c06.eff  b69f65798473cb07...  128 -> 130 emitters
          ef_elight_c07.eff  e6c6331d2f0f723c...  128 -> 130 emitters
```

## Build caveat, stated plainly

The shared plugin does **not currently compile**: the concurrent Ness back-throw
agent's `src/pgwr/plugin/src/mythra/ness_throw_b.rs` references an unlinked
`singletons` crate (2 × E0433). That file is not mine and was not edited. This
task's module was therefore compiled from an **isolated copy** of the plugin at
`builds/.cache/lucas-downsmash-verify/plugin` with only that one module removed.
The resulting NRO is a **verification artefact, not the package**: the installer
must build from the shared source once the concurrent work compiles, and compare
that NRO against the one recorded here. Nothing else differs.

## What is NOT established

Everything about behaviour. That the crate compiles, that 21 marker strings are in
the binary, that 66 bones survive a filter, that 622 sound tones are preserved
byte-for-byte, and that 128 emitters are still present - none of it says the
down smash plays, looks right, hits low, or is audible. No console run, no
emulator, no automated test. The test below is the first evidence that would
count.

## Artifacts

```
builds/pgwr/T-0060-lucas-downsmash/           package (delta only, not a full release)
  MANIFEST.json
  BASELINE_DELTA.json
  lucas_downsmash_sound.json
  lucas_downsmash_effect.json
  ultimate/mods/pyra_gamewatch_reskin/        24 mod files
builds/.cache/pgwr-fb-4-lucas-downsmash-target/      isolated cargo cache
builds/.cache/lucas-downsmash-effect_scratch/        effect converter work dir
builds/.cache/lucas-downsmash-verify/plugin/         the isolated compile copy
refs/lucas_attack_lw4/                     pins, provenance, inventory
refs/lucas_attack_lw4/inventory.json        measurements (tier B)
tools/audit_lucas_lw4_donor.py             donor + parser + bone-fit measurement
src/pgwr/tools/build_lucas_downsmash.py     the retarget
tools/apply_lucas_downsmash_motion_list.py  the 2-byte motion-list patch
tools/merge_lucas_downsmash_sound.py        the sound merge
tools/build_lucas_downsmash_effect.py       the effect merge
tools/audit_lucas_downsmash_delta.py        the scope/delta audit
```

## Tools re-run

```
python tools/audit_lucas_lw4_donor.py --check
python src/pgwr/tools/build_lucas_downsmash.py --check
python tools/apply_lucas_downsmash_motion_list.py --check
python tools/merge_lucas_downsmash_sound.py --check
python tools/build_lucas_downsmash_effect.py --check
python tools/audit_lucas_downsmash_delta.py --package builds/pgwr/T-0060-lucas-downsmash
```
