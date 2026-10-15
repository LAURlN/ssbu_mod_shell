# ACMD porting

Tiers: **A** hardware-confirmed (console or decoded crash report) - **B** measured offline by a script that still exists - **C** read from pinned third-party source - **D** hypothesis. Anything without a tier below is A/B unless marked otherwise. Paths in the source column refer to the *old* workspace (`modpack_test_1`); the same material now lives under `projects/*/history/`, `dumps/` and `evidence/`.

- ACMD alone is not a port: `game_downattacku` has no `change_motion`; statuses (`PreMain/Main/Init/ExitStatus/cleanup`) are native code in `lua2cpp_<fighter>.nro`. The donor dump repo has **zero** status functions for G&W (384 files: expression 352, sound 194, game 184, effect 103). (B)
- A script that exists on the recipient but not the donor keeps running (Pyra nair/bair sword trails on G&W). Derive the script set from the motion list; port what the donor has, empty what only the recipient has. (B)
- Dump conversion artifacts (rules R14-R21 in `gen_acmd.py`): printed `frame(false, N)`; `if call == X` rendered as discarded call + hardcoded `false == true`; `methodlua2cpp::L2CFighterAnimcmd<X>Common::fn()` is a real method; six macros exist only as raw bindings (`THROW_ITEM_OFFSET`, `SHOOT_ITEM_BULLET*`, `IS_HAVE_ITEM_KIND`, `DOWN_EFFECT`, `SET_RATE_ARTICLE_V`); donor article ids index past recipient table -> `if false`; ItemModule calls lose args -> list as unported, never guess. (B)
- Dumps are evidence, not drop-in code; maintainer states conversion errors exist. `smashline-hdr/` in that repo is a formatting variant, not HDR balance data. (movemakerguide)
- `smash_script::macros::CATCH` takes 11 values and always pushes 11 (`x2,y2,z2` -> empty `L2CValue` when `None`); verbatim signature in DIAGNOSIS 2026-09-17. (C) - see graveyard X-4: this was NOT why the grab failed.
- Log parsers drift silently: assert capture-group counts at start-up and keep a fixture (Monkey Flip log tool read `vpos.x` as distance). (process lesson, B)

## A sound-bank tone can reference other tones by index, and kind 1 is unhandled (2026-10-02)

**B: measured on the pinned `se_snake_c00` bank by
`tools/merge_snake_throw_lw_sound.py`, whose two negative controls are described
in `tools/README.md`.** Applies to any donor bank merge, not to ACMD text.

A `PLAY_SE(Hash40::new("some_tone"))` line names **one** tone, and appending
exactly that one tone can still be wrong, because the tone's own record can point
at **other tones in the same bank by index**. Those indices are
**bank-relative**, so after an append they silently resolve to whatever unrelated
tones happen to sit at those positions - and every existing check passes,
because a dangling-but-in-range index is a structurally valid bank.

Measured layout of a **kind-1** (sequence) tone record:

```text
name_at+0 ..        opaque header, then the tone's own name
payload_start+0      kind = 1
payload_start+4      payload_size = 8 + 16 * count
payload_start+8      0xFFFFFFFF
payload_start+12     count
payload_start+16     count rows of 16 bytes: (u32 flag, f32 weight, f32 ?, u32 CHILD INDEX)
                     then a 20-byte tail
```

`merge_hero_neutral_b_sound.group_links` decodes donor tone **kinds 0** (single
sample) and **3** (random group) and *asserts* on anything else - which is the
right behaviour and is what caught this. Snake's `se_snake_c00` has 111 tones:
102 kind-0, 8 kind-3, and exactly **one** kind-1,
`se_snake_catch_tight`, whose children are indices **92** and **93**
(`se_snake_catch_tight_01`, `se_snake_catch_tight_01_layer`). Appending it alone
into a 544-tone Pyra bank would have pointed it at two unrelated tones.

The rule this gives:

* **compute the transitive closure of a requested tone**, not just the requested
  names, and append the children with the parent;
* **rebase every child index** from donor index to merged index;
* then **resolve the links back to names in the written bank** and assert each
  one points at an appended tone. A byte-equality or preservation check cannot
  see this failure, because the record is perfectly well formed.

A negative control for it must restore the **donor** index, not merely any change:
the rebased value is what a correct merge produces, so perturbing it tests nothing.

## Porting an air attack whose landing is a second move (pikachu-airb 1.0.0, B, 2026-10-03)

`AttackAirB` and `LandingAirB` are two separate motions with two separate
scripts, so a "back air" port is really **two** ports that share a clip
retarget. Registering only `game_attackairb` leaves the generated G&W landing
running against a retargeted attack, and the mismatch is invisible offline: it
shows up as a landing whose hitbox and rumble are still Game & Watch's. Both
handlers of both kinds go in at the same `Priority::High`, because the generated
`acmd/generated/aerial.rs` and `acmd/generated/common.rs` entries are both
`Default`.

### Four things that cost time and are worth not paying twice

**1. A report that outruns the artefact is worse than no report.**
`build_pikachu_airb.patch_motion_list` computed the spliced entry, returned the
bytes in its JSON, and never wrote the file. The build report read "cancel
296->300, 2 bytes differ at [16, 62]" for both slots while the staged
`motion_list.bin` was byte-identical to the baseline. Nothing else noticed: the
clip hashes were right, the donor assertions were right, and the delta looked
complete. What caught it was the **delta audit re-reading the packaged file from
disk** and diffing it against the baseline. If a builder function returns bytes,
the assertion that matters is `read the file back`, not `return the buffer` -
and the audit that ships must never take the builder's word for a file.

**2. Copy the feature set from the baseline manifest; do not infer it.**
A first build with `--features hero-side-b` produced a 487424-byte NRO against
the baseline's 524288. The missing `hero-mana-hud` feature was the entire
difference, and a size check would have caught it while a "does it compile" check
would not. `builds/pgwr/0.20.23/MANIFEST.json` records the exact
`build_command`; that string, not the Cargo.toml defaults, is the specification.

**3. Build the unmodified snapshot too.** One extra build of a pristine copy of
the baseline source with the same command reproduced the baseline NRO
(`424914c18e74...`, 524288 B) **byte for byte**. That is the cheapest available
proof that the toolchain, feature set and environment match the release being
extended, and it turns "the NRO differs from the baseline" from a suspicion into
a statement: it differs *only* because of this task. Do this whenever a package
claims a new NRO hash.

**4. Convert a new source file to the tree's line endings.**
The repo's Rust files are CRLF (`core.autocrlf=true`), and `git apply` rewrites
to the platform default. An LF-authored module shipped in a patch and came back
from `git apply` as CRLF, so "the patch reproduces the live source byte for byte"
failed on a difference no compiler would ever see. Match the tree before you
generate the patch, not after.

### Move-identity facts specific to this pair

* **Both effects are common-bank.** `sys_spin_wind`, `sys_attack_impact` and
  `sys_down_smoke` are always-resident `sys_*` names, so a correct port merges
  **no donor emitter and touches no effect bank**. The same applies to
  `se_common_swing_02`, which the donor names for exactly that reason. The split
  is asserted by `audit_pikachu_airb_donor.py`, not assumed - if a donor ever
  moves a `sys_*` name into its own bank, that assertion fires instead of the
  move quietly playing nothing.
* **`PLAY_SEQUENCE` is not decoration.** `sound_attackairb` calls
  `PLAY_SEQUENCE(seq_pikachu_rnd_attack)`; that record names four
  `vc_pikachu_attack*` tones by CRC32. A Pyra bank without them resolves the
  sequence to **silence** with no error. Derive the tone set from the record and
  assert it is exactly the expected four.
* **`trans` is an engine anchor, not a model bone.** The donor's hitboxes are on
  `trans`, which is absent from both `model.nusktb` files, exactly like `top` and
  `havel`. Do not remap it and do not report it as a missing bone.
* **No status id is consumed.** `AttackAirB` and `LandingAirB` are vanilla
  states on both fighters, so a port of both needs no free status id and adds no
  `config.json` entry.

**5. Check `$?`, not the tail of the output.** Every earlier run of the
pikachu-airb delta audit had been piped through `tail`, which reports the
pipeline's status and hides the tool's. Re-run with the status captured, the
`--negative-controls` mode was found to **exit 1 on a fully passing run** and to
print `FAIL: 0 control(s) not caught`. The cause was a status flag shared under
two opposite senses: damage controls stored `caught: True` when the audit
*rejected* them, while the positive control stored `caught: not ok` — so "not
caught" meant "correctly rejected" for eight rows and "correctly accepted" for
one, and the exit test read the wrong one. Every control now carries an explicit
`ok` plus a `kind` (`damage` or `positive`), and the summary reports the two
counts separately. Two rules follow:

* a control's result must not share a boolean key with another control whose
  meaning is inverted — name the polarity (`ok`) and record which polarity
  applies (`kind`);
* **an exit code of 0 proves nothing until the failure path has been shown to
  fire.** Here that was done by temporarily replacing one damage function with a
  no-op in the real file, requiring a non-zero exit, then restoring the file and
  re-checking its sha256. Do that for any check whose only evidence is "it
  passed".
