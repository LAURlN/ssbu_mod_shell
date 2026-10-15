# Handoff to Space Bunny Alpha: Pyra c06/c07 → Mr. Game & Watch

Written 2026-09-29. Workspace: `<workspace root>`.
Project folder: `mod_files/pyra_gamewatch_reskin/`. Output: `mod_output/pyra_gamewatch_reskin/`
(an SD-root tree). Read `README.md` in this folder first.

## Direction change: read this before anything else

The user **stopped** both earlier approaches:

- `pyra_mythra_clone/` (Clone Engine standalone pair). It is parked; do not continue M0/M1 there.
- `mod_files/mythra_gamewatch_swap/` (hooking Mythra into real G&W). It is parked.
  Reuse knowledge and code from it, but don't build on its swap hooks.

The new plan: **Pyra's c06 and c07 costumes become Mr. Game & Watch.** Mythra
stays vanilla, so the game's own Pyra↔Mythra down-B swap is the transformation.
That removes the swap and camera bugs and the Clone Engine crashes. The remaining
work is a moveset port: G&W's moves, stats and articles, running on Pyra's
fighter kind (`eflame`) and gated to costume slots 6 and 7.

## State: prototype 0.1.0, console-verified by the user on 2026-09-29

Assets only, no plugin. `build.py` produces it. What the user saw on hardware:

- Nothing crashes. Vanilla Pyra and every Mythra slot are unaffected.
- Pyra c06/c07 show the G&W model and animations, with the down-B swap working.
- They **behave like Pyra**: her hitboxes, specials, stats and effects. Some
  visuals are "a bit buggy" (expected: Pyra's scripts and timings driving G&W
  clips, 8 motion kinds that fall back to `wait`, Pyra's fire effects on `sword1`,
  and the Aegis article model left vanilla).

How the prototype works, and the constraints that come from it:

- **Never introduce a file name Pyra doesn't already have.** New names didn't
  load in the earlier project. G&W textures are written over Pyra texture names;
  Pyra's `motion_list.bin` is unchanged and her clip files are overwritten with G&W
  clips. If you need a new motion kind or file, prove on hardware that the
  mechanism works before depending on it (or hand back).
- The skeleton is G&W's, with 120 Pyra-only bones grafted on at Pyra's bind pose
  (`sword1`, `sword2`, `h_*`, fingers, hair). Pyra's scripts attach hitboxes to
  `sword1`/`haver`. G&W's scripts only use G&W bones, which are all present.
- Tooling: `scratch/py312/python.exe` (embeddable 3.12 with numpy and the vendored
  `ssbh_data_py` on its path). System Python is 3.8 and can't load the vendored module.

## SD card state (F:)

Installed: ARCropolis, `libarc_network.nro` (keep it: dumping depends on it),
`libsmashline_plugin.nro`, `libnro_hook.nro`, and `ultimate/mods/pyra_gamewatch_reskin`.
Everything else was removed and backed up to `sd_backups/2026-09-29_before_pyra_gw_reskin/`.
Do not reinstall Clone Engine, CSK collection or the trace plugin.

## What to work on, in order

Every change must only affect `eflame` slots 6 and 7. Vanilla Pyra c00–c05, every
Mythra and every real G&W must stay exactly vanilla. Check this in every console test.

### Phase 1: plugin skeleton and gating

New crate `mod_files/pyra_gamewatch_reskin/plugin/` (Skyline, smashline 2). Copy the
dependency setup and the rationale comments from `mod_files/mythra_gamewatch_swap/Cargo.toml`.
The no-`rev` / no-`[patch]` rule there was learned the hard way. Keep `Cargo.lock` pinned.
Use `smashline::Agent::new("eflame").set_costume(vec![6, 7])`, which exists in the locked
source (`crates/smashline/src/builder.rs`). Confirm that it actually restricts to those
slots on hardware with one visible change (for example, G&W's jab `game` script) before porting in bulk.
Put the slot list in one constant.

### Phase 2: ACMD port (normals, aerials, grabs, throws)

Source: `SSBU-Dumped-Scripts-main/smashline/lua2cpp_gamewatch`. Follow
`.agents/rules/movemakerguide.md` and `move_replacement_guide.md`. The dumps can
contain conversion errors, so treat them as evidence, not truth.

- Port `game`, `effect`, `sound` and `expression` for every non-special move under
  Pyra's motion-kind names, overriding every Pyra script those slots can reach.
  Any Pyra script you miss still puts sword hitboxes on G&W's body. Keep a table:
  Pyra motion kind → G&W source script → status.
- Where the motion kinds differ, change the assets, not only the scripts. For
  example, Pyra's jab is `attack_11/12/13` and G&W's is `attack_11` plus
  `attack_100`. Extend `build.py`'s motion mapping instead of hand-copying files,
  and keep `build-record.json` current.
- Effects and sounds named `gamewatch_*` / `se_gamewatch_*` are probably not
  loaded for `eflame`. List every one that is used. Substitute common (`sys_*`, `se_common_*`)
  where a substitute is obvious, and leave the rest for a later one-slot
  effect/sound pass. Don't guess at loading G&W banks.
- Disable Pyra-specific visuals on these slots: Aegis sword effects and
  expression scripts that reference Pyra meshes.

### Phase 3: stats

Use G&W's `fighter_param` values (weight, walk/run/air speeds, jumps, gravity,
fall speed, shield, ledge, ECB and the rest) for `eflame` slots 6 and 7.
`lib_paramconfig` is in the cargo cache (`~/.cargo/git/checkouts/lib_paramconfig-*`).
A per-slot param config plugin is the preferred route over hand-written hooks.
Read its source first to confirm it supports per-slot `eflame` overrides. Generate
the values from `export/fighter/common/param/fighter_param.prc` with a script;
don't type them by hand. Model scale is a param too: compare G&W's rendered size
with the real one.

### Phase 4: specials, one at a time

Order: up-B (Fire), side-B (Judge), neutral-B (Chef), down-B last.
**Down-B stays the vanilla Pyra→Mythra swap.** That is the whole point of this
design, so do not replace it with Bucket. Specials need statuses (smashline status
scripts on the gated agent) and usually articles. `smashline::clone_weapon` exists in
the locked source (`src/lib.rs`, `clone_weapon(original_owner, article_id,
new_owner, new_name, use_original_code)`). Test it with one G&W article (the
Chef sausage or Judge) before building anything on it.

## When to hand it back (stop and write a report)

Hand back to the user, who will pass it to Claude, at any of these points:

1. **Phase 2 is done and console-tested.** All normals, aerials, grabs and throws on
   c06/c07 behave like G&W, and vanilla slots are confirmed unchanged. This is the planned checkpoint.
2. `set_costume` gating **does not isolate the slots** on hardware (vanilla Pyra
   or Mythra changes). The architecture depends on it.
3. Anything needs **new file names** or new motion kinds, or a **raw-offset
   Skyline hook** (`from_offset`, hooks into `main`). Stop before you write it.
4. A **crash you can't explain** after two hypothesis-driven attempts.
5. `clone_weapon` or the param-config route turns out to be unworkable.
6. Something in the handoff turns out to be wrong.

Do not stop for ordinary per-move bugs. Log them and keep going.

## Working rules

- Build output goes under `mod_output/`, source under `mod_files/`.
- **SD card: installing is the agent's job.** (Changed 2026-09-29. This used to
  read "only install when the user asks" — that rule was self-imposed and it
  caused a real failure: the card silently ran a 0.8.x build against an unpatched
  smashline plugin, every prop was missing, and the result looked like a code
  bug. Do not print copy instructions and stop. Run
  `mod_files/pyra_gamewatch_reskin/install-to-card.sh`, or
  `build-plugin.sh` with no arguments, which installs as its last step.
  `build-plugin.sh --stage-only` is the only way to skip it.
  The script finds the card by its own contents rather than a remembered drive
  letter, backs up every overwrite into a timestamped `sd-backup-*/`, stages and
  verifies the 793-file mod tree before swapping it, verifies everything by hash
  afterwards, and **rolls back automatically** if verification fails. Use it
  rather than hand-copying; do not reimplement the copy by hand.
  Never touch `libarcropolis.nro`, `libarc_network.nro` or `libnro_hook.nro`.
- **Testing is the user's job, not yours.** The console cannot be driven from
  here. Hand back a build that is installed and verified, a list of exactly which
  log lines and observations would confirm or refute it, and the location of the
  newest Atmosphère crash report if it crashes. Do not describe a build as
  working until the user has run it.
- Record every console test in `reports/console-YYYY-MM-DD-runN/` (the user's
  observations and the logs), with a short "expected vs. seen" note.
- Before handing back, update `README.md` (state, what's installed, next console
  test) and add a short "Space Bunny Alpha report" section at the end of this file.
  It should cover what's done, what's console-verified vs. only built, open bugs,
  and why you stopped. Say plainly what was not tested.
## Space Bunny Alpha report

Written 2026-09-29 by Space Bunny Alpha. Covers phase 1 only.

### Stopped here because

The handoff says to confirm `set_costume` gating "on hardware with one visible
change ... before porting in bulk", and lists "set_costume gating does not isolate
the slots on hardware" as handback point 2. I built exactly that: the plugin
skeleton plus one visible change (G&W's jab), and stopped for the console test
rather than porting ~30 moves onto a gate that might turn out not to hold.

This is **not** the phase-2 checkpoint. Phase 2 is untouched.

### What is done

**Plugin crate** `mod_files/pyra_gamewatch_reskin/plugin/` (Skyline + smashline 2).
`Cargo.toml` and `Cargo.lock` are the parked crate's, retargeted and retitled;
every dependency revision is unchanged and must not be updated. Compiles clean
with no warnings.

**Gating.** `src/lib.rs` holds the only costume list in the crate:

    pub const TARGET_COSTUMES: [usize; 2] = [6, 7];

Every override is registered as
`Agent::new("eflame").set_costume(TARGET_COSTUMES.to_vec())`. I read the locked
smashline to confirm this gates at *install* time rather than at call time
(`src/create_agent.rs`, `install_script`): it computes `has_costume(hash, colour)`
and only calls `sv_set_function_hash` when the agent's own colour is listed. An
eflame agent in c00-c05 therefore never gets our script pointer at all. So the
ported functions contain no costume `if` and no `else` branch that could drift
from vanilla. `elight` and `gamewatch` are never registered with smashline, so
Mythra and the real G&W are not merely gated but absent from the plugin.

**Jab port** `src/acmd/attack11.rs`, from
`SSBU-Dumped-Scripts-main/smashline/lua2cpp_gamewatch/gamewatch/Attack11.txt`.
`game`, `effect`, `sound` and `expression` for `Attack11`. Damage, angle, KB,
hitbox offsets, frame timings, the `ENABLE_100` rapid hand-off, the foot effect,
the slope read and the rumble are the dump's values unchanged.

**Sound tool** `tools/sound_names.py` + `sound-inventory.json`. Recovers sound
names from `<bank>.nus3audio` and validates each against the `<bank>.tonelabel`
keys (low 32 bits of Hash40 = crc32 of the name). Result: 111 eflame sounds are
resident, and **67 G&W sounds are unreachable from eflame**. This is the
evidence base for the sound substitutions, not a guess.

**Phase-2 table** in `src/acmd/mod.rs` maps every non-special Pyra status to its
G&W source and marks it ported or todo, so adding a move is one line that cannot
drift from what is installed.

### The three things that could not be copied verbatim

These matter for phase 2 and are the reason the port is not mechanical:

1. **G&W work ids are raw indices, not symbolic names.**
   `FIGHTER_GAMEWATCH_INSTANCE_WORK_ID_INT_NORMAL_WEAPON_KIND` is `0x100000BD` in
   `lua_const.rs`. Pyra's ranges are float `0x4B`-`0x4C` and int
   `0x100000BF`-`0x100000C3`. Writing G&W's index into an eflame agent hits
   Pyra's own storage. **Every G&W work id used by a ported move needs a
   translation table.** That is the main phase-2 hazard.
2. **G&W's article ids do not exist on Pyra.** G&W's jab spawns
   `GENERATE_ARTICLE_NORMAL_WEAPON` = index `0x5`; eflame's
   `ARTICLE_TERM` is `0x5`, so she has 0-4 only. The generate call is omitted
   rather than attempted out of range. Consequence: no little prop on the jab.
   Deferred to phase 4 with `clone_weapon`.
3. **Sounds.** Substituted with `se_eflame_swing_s01`, verified resident in
   eflame's bank. The export contains **no common/system SFX bank** (the only
   non-`fighter/se_*` banks are fighter_voice and narration), so a `se_common_*`
   or `sys_*` substitute could not be verified and was not used. The handoff
   suggests those; I am flagging that they are unverifiable from this dump.

One known no-op, kept for faithfulness to the dump: G&W's expression script
swaps mesh visibility `head` -> `head_none`, but G&W's `model.numdlb` has neither
name (its head meshes are `HeadM_VIS_O_...` / `HeadBM_VIS_O_...`; the bone is
`Head`). The jab's face will not change. Dump/model name mismatch, not a port bug.

Also worth recording: `top` in the ATTACK calls is **not a bone**, it is Smash's
built-in "fighter top" anchor, so the jab hitboxes do not depend on the grafted
skeleton at all. G&W's c06 skeleton is fully present in the grafted output (0
G&W bones missing, 165 total).

### Verified on the Switch

Only the 0.1.0 assets-only build, which the user tested on 2026-09-29: loads,
G&W appears on c06/c07, down-B swap works, no crashes, vanilla Pyra and every
Mythra slot fine.

**Nothing in 0.2.0 has been on hardware.** The plugin has never been loaded. The
jab has never run on a Switch. The gating has never been exercised.

### Only built, never run

Everything listed under "What is done" above. In particular: that `set_costume`
actually isolates c06/c07, that the jab produces G&W's hitboxes in the right
place, and that nothing crashes. A clean compile proves none of that.

### Installed on the SD card (F:) 2026-09-29

    atmosphere/contents/01006A800016E000/romfs/skyline/plugins/
      libpyra_gamewatch_reskin.nro
        7fdcfadd5dd3bb02d879a64db32df5e88c0db9fb8b3507ff1fc1bd6ecb849b01   49152 bytes
    ultimate/mods/pyra_gamewatch_reskin/info.toml                          (0.2.0)

Verified by hash after copying. The 716 model/motion files were **not**
re-copied: `build.py` reproduces them byte for byte, and `diff -rq` against F: is
now clean. The four framework plugins were re-hashed after the install and are
byte-identical to their pre-install values:

      c7644991dec05224de7c4792e0c8a7b33acd1f1c0711a630df9e1f5ec1a5294e  libarc_network.nro
      49b6f634039f0b2f9bd9e28cf0d04bfda16ad5fbef67b3994032cc43d80441a7  libarcropolis.nro
      ca7aec03aee49fea539dcb92569fea5bc5389f77377ba2a30e4d0b7ebd0255e6  libnro_hook.nro
      5f4091eed89c5854c2bfccb9f25b6e8da8c03ebedcaa5ab36eadebfc078bc8f7  libsmashline_plugin.nro

Backup of the replaced `info.toml`:
`sd_backups/2026-09-29_before_pgwr_0.2.0/info.toml.bak`.

To revert: delete `libpyra_gamewatch_reskin.nro`. Nothing else is required.

### Console test to run now

Log to read: `/atmosphere/.../smashline_smashlog.txt` (or whatever your usual
Skyline log path is). Filter on `[PGWR]`.

Expected at boot, exactly once each:

    [PGWR] Pyra G&W reskin plugin v0.2.0 (phase 1: gating + jab) loaded
    [PGWR] gated fighter=eflame costumes=[6, 7]
    [PGWR] NOT registered: elight (Mythra), gamewatch (real G&W)

If the first line is missing, the NRO did not load and nothing below is
meaningful. If smashline prints its own `Script ... replaced by` line, that is
expected and harmless.

1. **Load Pyra c06** (7th colour swatch). Jab a CPU.
   *This is the point of the whole test.* The jab must produce G&W's hitbox: a
   short poke at the fighter's top, 3% per hit, with a clear hitstop. It must
   NOT produce Pyra's long sword arc. No little prop appears - expected, see
   above.
2. **Load Pyra c07** (8th swatch). Same jab. Same result.
3. **Load vanilla Pyra c00 through c05, one at a time.** Jab each.
   **These must be completely unchanged: Pyra's own sword jab, Pyra's own
   sound, Pyra's own arc.** If any of them changed, the gate does not hold -
   stop and report that, it is handback point 2.
4. **Mythra, any colour.** Jab. Must be exactly vanilla. Down-B to Pyra and back,
   then jab on both sides: Pyra side c06 only should be G&W, every other colour
   should be Pyra.
5. **Real Mr. Game & Watch**, any colour. Must be exactly vanilla, G&W's own
   jab. We never register him.
6. **Hit and be hit** on c06/c07. Note where the hitbox sits and whether the
   G&W model animates correctly. No crash expected.
7. **Down-B on c06/c07**, several times, ground and air. Must still be the
   vanilla Pyra<->Mythra swap. We did not touch it; confirm anyway.
8. **Specials on c06/c07** (side-B, up-B). These are still Pyra's and are
   expected to look wrong (Aegis sword on a G&W body). Just confirm no crash.

What would tell me to stop: a crash, vanilla c00-c05 or Mythra changing at all,
or the jab hitbox appearing on a slot that is not c06/c07.

### Open items carried into phase 2

- The G&W -> eflame work-id translation table does not exist yet. It is the
  first thing phase 2 needs, and the jab happened not to need one.
- Pyra's jab is a three-status chain (`Attack11` -> `Attack12` -> `Attack13`);
  G&W's is `Attack11` plus an `Attack100` rapid. All three Pyra names must be
  overridden or Pyra's 2nd and 3rd hits keep putting sword hitboxes on G&W's
  body. This is the highest-priority phase-2 item.
- `build.py`'s motion mapping needs extending for `attack_100` (rapid fire) and
  the other G&W-only motion kinds, not by hand-copying files.
- Remaining G&W effects still need auditing; only the jab's have been checked so
  far, and its one effect name (`null`) is generic.
- Pyra-specific visuals (Aegis sword effects, expression scripts referencing Pyra
  meshes) are not yet disabled. Phase 2.
---

## Space Bunny Alpha report - phase 2 addendum

Written 2026-09-29. Phase 2 is built and installed; the console test is pending.

### Console run 1 (0.2.0) verdict: INCONCLUSIVE

Recorded in `reports/console-2026-09-29-run1/RESULT.md`. The jab was reported as
"kinda hard to tell, but I think the jab is working", and the negative control
(vanilla c00-c05 / Mythra / real G&W unchanged) was never explicitly confirmed.

That cannot distinguish a working gate from a gate that failed open, and gating is
load-bearing for the whole design. Two mitigations are in 0.3.0:

- **`gate_trace`**, a `Main` line callback registered on the *same* gated agent as
  the ACMD overrides. smashline only installs it for c06/c07, so a line reading
  `GATE ACTIVE: entry N ... colour C` is positive proof the gate holds on that
  fighter, and the absence of such lines for c00-c05 in the same match is the
  negative control. Gating is now a log reading, not a judgement call.
- Phase 2's moves are individually distinguishable (G&W's jab is 3% x3 at the
  fighter top, his dash is 10%/6.5% at the head, his aerials are 6-8% body
  hits), so a positive result is obvious where the jab alone was not.

### What phase 2 covers

**31 Pyra statuses, 124 ACMD functions**, from 27 G&W donor scripts:

- ground: Attack11/12/13, AttackDash, AttackHi3, AttackHi4(+Charge), AttackLw3,
  AttackLw4(+Charge), AttackS3, AttackS3Hi, AttackS3Lw, AttackS4(+Charge),
  DownAttackU, DownAttackD
- aerials: AttackAirN, AttackAirB, AttackAirF, AttackAirHi, AttackAirLw
- grabs/throws: Catch, CatchAttack, CatchDash, CatchTurn, CatchWait,
  ThrowF, ThrowB, ThrowHi, ThrowLw

Specials and the down-B swap are untouched, by design.

### The port is generated, not hand-written

`tools/gen_acmd.py` emits `plugin/src/acmd/generated/{ground,aerial,grab}.rs`
from the dumps, and `gen_acmd.py --check` proves the checked-in files still match
the generator. Eleven transformation rules (R1-R11) are listed in the generator
with the reason for each, and every drop is recorded in a `GEN-NOTES` header in
the file it happened in. `generated-manifest.json` records the donor script and
status list per group.

Hand-writing ~110 functions risks a silently mistyped hitbox; generating makes
the translation reviewable as a rule list instead of a diff.

### What the analysis found before writing any code

`tools/analyse_port.py` + `port-dependencies.json` checked what the 27 non-special
G&W scripts actually need to run on eflame. This substantially changed the plan:

- **Zero `gamewatch::ST_*` status kinds.** No status translation is needed for
  phase 2 at all.
- **One G&W work id, in the jab only.** The work-id translation table I expected
  to be phase 2's main hazard turned out to be needed in exactly one place.
- **No `gamewatch_*` effects.** All six effect names are `sys_*` or `null`, which
  are the common family and should load as-is.
- **One ATTACK bone: `top`**, which is not a bone but Smash's built-in fighter-top
  anchor. So hitbox placement never depends on the grafted skeleton.

### Two real bugs caught by reviewing the generated output

Both would have shipped silently, which is the argument for generating plus
reviewing rather than doing either alone:

1. **G&W work-index writes survived.** R1 only matched `ArticleModule::`, so
   `WorkModule::set_int(..., *FIGHTER_GAMEWATCH_INSTANCE_WORK_ID_INT_NORMAL_WEAPON_KIND)`
   in the aerials passed through and would have written G&W's raw index
   `0x100000BD` into Pyra's work array. Fixed by R6, which matches on the
   *constant* rather than the call, because the call can be `set_int`, `set_float`,
   `on_flag`, `off_flag` or `clear_all`. Never assume dropping an article drops
   its work id.
2. **A dead branch in the smashes.** The dump renders Lua's
   `if WorkModule.is_flag(...) then` as a discarded call followed by
   `if(methodlib::L2CValue::operator==(lib::L2CValueconst&)const(false, true)){`
   - a hardcoded `false == true` that never runs. Left alone, the body guarded by
   it (hand/hold mesh swaps during the side smash) would have silently stopped
   executing. Fixed by R11.

R8-R11 are further dump-vs-toolchain mismatches the first compile exposed:
`set_attach_item_visibility` needs a third `u8`, `set_default_int64` takes
`c_ulong` and not a `Hash40` struct, `AREA_WIND_2ND_arg10` must go through the
smash_script macro (the raw symbol takes only the lua_State), and `set_int64`
takes `u64` where the dump prints `i64`. This is the conversion-error risk
movemakerguide.md warns about, and every one is now a documented rule.

### Deliberate omissions, and what they cost

- **Articles (R1).** G&W's articles run 0-8; eflame's `ARTICLE_TERM` is `0x5`.
  So G&W's jab and down-smash prop, his forward-air bomb and his up-air breath
  are all absent. **Forward air is a body hit instead of a bomb drop and up air
  is a body hit instead of a tether-breath.** Those are the two moves where this
  is most visible; both are phase 4 work with `clone_weapon`.
- **Sounds (R2).** All 21 `se_gamewatch_*` names are unreachable from eflame and
  are mapped by role to verified-resident eflame sounds (`se_eflame_swing_s01`
  and friends). `se_common_throw_02/03` are kept verbatim: they name the common
  bank, which is resident for every fighter. That is an inference from the name,
  not a verified fact, because this export has no common SFX bank. **G&W's
  signature tooting will not be reproduced** - he will sound like Pyra swinging a
  sword. A later one-slot pass is the place to fix this properly.
- **`CaptureDamageLw` not ported.** Pyra's is a single `slope!` expression with
  no hitbox or effect, so it cannot put sword hitboxes on G&W's body. G&W's
  counterpart calls an internal binding absent from the locked toolchain. Left
  as Pyra's.
- **One unresolvable raw hash.** `notify_event_msc_cmd!(Hash40::new_raw(0x28f4e20a43))`
  in AttackLw3 and AttackS3. It could not be resolved to a name and these are
  NRO-relative per the project's rules, so it is dropped (R3) rather than guessed.

### Asset side

`build.py` now records exactly which motion kinds fall back to `wait`, instead of
just counting them. Pyra's `attack_100_start` was one: it is the wind-up for her
rapid jabs, which G&W does not have, and it was playing `wait` while the
override fired G&W's `Attack11`. Now mapped to G&W's `attack_100`.

**No phase-2 move's motion falls to `wait`.** The 8 remaining are 10 unnamed
hashes with no `ParamLabels` entry, Wario-bite grabbed states, three `fill_blank_*`
idle fillers, and `visual_scene_01/02`.

`visual_scene_01/02` is worth knowing about: those are Pyra's transformation
scene, so during down-B to Mythra the G&W model will stand still for the cutscene.
G&W has no transformation scene to borrow, and Mythra stays vanilla by design, so
this is inherent to the approach rather than a missed mapping.

The other asset news is good news: Pyra's and G&W's motion names already agree on
the smashes (`attack_s3_s`, `attack_s4_s`, `attack_hi4_hold`, `attack_lw4_hold`,
`attack_s4_hold`), so the smashes were never falling back - my first check used
status names where motion names were needed.

### Verified on the Switch

Still only the 0.1.0 assets-only build (user, 2026-09-29). The 0.3.0 plugin has
**never been loaded on hardware**, and neither has the gate trace.

### Only built, never run

All 124 ACMD functions, the gate trace, and the `attack_100_start` asset fix. A
clean compile with zero warnings proves only that it builds. In particular it
does not prove the hitboxes land correctly, that no G&W constant slipped through,
or that nothing crashes at runtime.

### Installed on the SD card (F:) 2026-09-29

    atmosphere/contents/01006A800016E000/romfs/skyline/plugins/
      libpyra_gamewatch_reskin.nro
        3d66957ce3785c779350a3355b13a3e118b033c079bfada6bc1424663e6ae18e   81920 bytes
    ultimate/mods/pyra_gamewatch_reskin/info.toml                          (0.3.0)
    ultimate/mods/pyra_gamewatch_reskin/fighter/eflame/motion/body/c06/c00attack100start.nuanmb
    ultimate/mods/pyra_gamewatch_reskin/fighter/eflame/motion/body/c07/c00attack100start.nuanmb

All copied and verified by hash; `diff -rq` against the built tree is clean. The
four framework plugins were not touched. Rollback: the 0.2.0 NRO and info.toml are
in `sd_backups/2026-09-29_before_pgwr_0.3.0/`.

### Console test to run now

Filter the log on `[PGWR]`. At boot:

    [PGWR] Pyra G&W reskin plugin v0.3.0 (phase 2: normals, aerials, grabs, throws) loaded
    [PGWR] gated fighter=eflame costumes=[6, 7]
    [PGWR] NOT registered: elight (Mythra), gamewatch (real G&W)

smashline may also print its own `Script <hash> of ... replaced by ...` lines. That
is expected and is how it reports each of the 124 overrides. If you see
`already exists` or `will be bypassed` for any of ours, that is a real problem -
report the line.

**The gating check, which is the point of this run.** In one match, load Pyra
c06 and jab. You must see:

    [PGWR] GATE ACTIVE: entry 0 running c06/c07 overrides, reported colour 6

Then in the same match, switch to c00 and jab: **no new GATE ACTIVE line**. A line
naming a colour outside 6/7 is a gate failure - stop and report it.

**The moves.** On c06 and c07, check each against real G&W:

1. Jab, then hold jab for the rapid. 3% x3, then fast repeat pokes. No prop.
2. Dash attack. 10% then 6.5%, hits high at the head. G&W pokes you with a
   forward headbutt, not a sword.
3. Up tilt, down tilt, side tilt. G&W's are short jabs of the hand/foot.
4. Up smash, side smash, down smash. Note the down smash no longer has the prop.
5. All five aerials. Forward air and up air are body hits only - no bomb, no
   breath. That is expected, see above.
6. Grab, pummel, then each of the four throw directions. G&W's throws are his
   distinctive tosses.
7. Down attack (up and down) from a ledge or crouch.
8. Down-B to Mythra and back, on the ground and in the air. Must still be the
   vanilla Pyra<->Mythra swap. G&W will stand still during the cutscene.
9. Specials: still Pyra's. Expect the Aegis sword on a G&W body. Just no crash.

**The control, which must be checked deliberately.** Vanilla Pyra c00-c05: every
move must be exactly Pyra's, with her sword arcs and her sounds. Mythra any
colour: vanilla. Real Mr. Game & Watch any colour: vanilla, with his bomb-drop
forward air. If any of those changed, the gate failed - stop and report.

### Open items carried into phase 3/4

- Stats are still Pyra's: weight, speeds, jumps, gravity, shield, ledge, ECB and
  model scale. This is why c06/c07 will not yet feel like G&W even if every move
  above is correct.
- Articles: forward air (bomb), up air (breath), and the jab/down-smash prop.
  Needs `clone_weapon` tested on one article first.
- The 21 G&W sounds are approximated, not reproduced.
- `visual_scene_01/02` play `wait` during the swap.
- Phase 4 specials, in the handoff's order: up-B, side-B, neutral-B, down-B last
  and never replacing the vanilla swap.

---

## Space Bunny Alpha report - run 2 (0.3.0) and 0.4.0

### Console run 2: what actually happened

"yup, it's mostly right now, the animations are a bit weird here and there, there
are still some leftover animations from Pyra, especially the sword, and usually I
find a second or even more G&W on top of each other. but no crash."

Recorded in `reports/console-2026-09-29-run2/RESULT.md`.

**Gating is still unverified.** Asked directly, the answer was "I didn't test the
vanilla slots". This is the one thing that gates confidence in everything else,
because if the gate does not hold then "mostly right" could mean "right on some
slots and silently wrong elsewhere". It is the first item of the next test.

### Root cause of the leftover Pyra animations - found and fixed

The rapid-fire chain was never ported. G&W's `Attack11` sets
`FIGHTER_STATUS_ATTACK_FLAG_ENABLE_100`, which hands over to `Attack100`. So a
single jab landed G&W's hitbox and then dropped straight back into Pyra's
0.6% magic pokes, with `effect_attack100` still spawning `eflame_attack100_hand`
and `eflame_attack100` on G&W's body. That is the "leftover Pyra animations".

0.4.0 ports `Attack100`, `Attack100Sub` and `Attack100End` from G&W, in a new
`generated/rapid.rs`. G&W's rapid is 0.8% `collision_attr_rush` pokes ending in
`Attack100End`, a large launcher.

`Attack100Start` is left as Pyra's: it is two lines, a motion-rate change and
`se_common_swing_04`, with no hitbox, effect or article.

Two new generator rules came out of this:
- **R12** drops any line naming an `eflame_*` or `elght_*` effect handle. Added as
  a backstop after finding `effect_attack100` still spawning Pyra's handles. It
  did not need to fire for the G&W donors, because their scripts do not name Pyra
  effects; the real fix was porting the status. Recording that honestly: R12 is
  insurance, not the cure.
- **R13** rewrites the bare `wait_loop_sync_mot()` in G&W's rapid-fire to
  `sv_animcmd::wait_loop_sync_mot(agent.lua_state_agent)`. Same family as R10 -
  the dump calls the raw symbol with no arguments, but the binding takes the
  lua_State. There is no `macros::` wrapper for this one.

### The duplicate G&W - not yet diagnosed

The clarification "from the very beginning, during movement and most animations,
only disappears during some animations and comes back afterwards" rules out the
windummy theory: `windummy` is only generated in `Win3`/`Win3Wait`, the win poses.

Current working hypothesis, **not confirmed**: the dormant Aegis partner is being
drawn as a G&W. The supporting evidence is that `EntryL` and `EntryR` - the spawn
scripts - generate `FIGHTER_EFLAME_GENERATE_ARTICLE_DIVER`, which is the partner
body, and eflame has no model directory of its own for it, so it would resolve
through `eflame/model/body`, which is exactly the folder this mod overwrites.
"From the very beginning" matches `EntryL` precisely.

I have not been able to confirm this from the dumps, and I am not going to
change the model layout on a hunch. If it is the partner, the obvious "fix" -
writing G&W files into `fighter/elight/model/body/c06` - would turn real Mythra
c06 into G&W and break the rule that Mythra stays vanilla, so it needs the
diagnosis first.

The decisive test is in `reports/console-2026-09-29-run2/RESULT.md`: spawn as
Pyra c06, press nothing, then press down-B. If the second figure becomes Mythra
while the first stays G&W, it is the partner. If it does not change, it is an
article and the hypothesis is wrong.

### 0.4.0 installed

    atmosphere/contents/01006A800016E000/romfs/skyline/plugins/
      libpyra_gamewatch_reskin.nro
        83b42b933be99dca70392e895bb4d5e5c30304f3a9629c03c781f45b2bd29c0e   81920 bytes
    ultimate/mods/pyra_gamewatch_reskin/info.toml                          (0.4.0)

Verified by hash and `diff -rq`. Rollback: `sd_backups/2026-09-29_before_pgwr_0.4.0/`.
Builds with zero warnings. Generator and asset build both reproducible.

### Still only built, never run

0.3.0 has now run. 0.4.0 has not. Nothing about the rapid-fire fix, and nothing
about the duplicate, is verified on hardware.

### Next console test, in priority order

1. **The negative control.** Vanilla Pyra c00 through c05, jab and rapid-fire each.
   Must be entirely Pyra. Then Mythra any colour, and real G&W any colour. This
   has now been skipped twice and it is the foundation of the whole approach.
2. **The gate proof.** In the log, one `[PGWR] GATE ACTIVE: entry N ... colour C`
   line for c06/c07, and no such line for c00-c05 in the same match.
3. **The rapid-fire fix.** Jab once, then hold jab. Should be G&W's 0.8% rapid
   pokes, no Pyra magic effects, no Pyra hand effect. Then let the rapid finish
   into `Attack100End` and check it is G&W's launcher.
4. **The duplicate.** The down-B test above.

---

## Space Bunny Alpha report - run 3 (gate confirmed) and 0.5.0

### The gate is CONFIRMED

The user tested the vanilla slots: "i tested the vanilla ones they work fine."

This is the negative control that had been missing since run 1. `Agent::new("eflame")
.set_costume([6, 7])` really does restrict the overrides to c06/c07, and vanilla
Pyra c00-c05, Mythra and real G&W are untouched. **Phase 1's design risk is
retired.** The whole approach now rests on a verified fact rather than a reading of
smashline's source.

### Forward air and up air: clone_weapon is unworkable, and it is provable

The user asked for G&W's f-air bomb and u-air breath. The handoff's instruction was
to find the weapon index before attempting the one-article test, so I did.

`smashline_clone_weapon` (locked smashline `be3ef308`, `src/api.rs:304`) does:

```rust
let original_name = LOWERCASE_WEAPON_NAMES.get(original_article_id as usize).unwrap();
```

and `LOWERCASE_WEAPON_NAMES` is a `StaticArrayAccessor` at **`0x5186bd0`**. The
project's own lessons log records that the correct 13.0.4 table is at
**`0x5185bd0`** and that smashline's name tables are each displaced by `+0x1000`.

I confirmed that from the user's own pinned `references/mythra_gamewatch_feasibility/main_memory.bin`.
The weapon-name struct is 24 bytes: `{name_ptr, table_ptr, 0x403}`. Reading the
`table_ptr` of two known entries:

| weapon | table_ptr | index if base `0x5186bd0` | index if base `0x5185bd0` |
| --- | --- | --- | --- |
| `breath` | `0x5185f40` | **-402** | 110 |
| `normal_weapon` | `0x5185fc0` | **-386** | 126 |

Negative indices under the base the locked build uses. That is a direct
confirmation of the displacement, from the user's dump, for this specific table.

**Consequence:** `clone_weapon` would look up the wrong name for any real weapon
index, and `.unwrap()` on an out-of-range `get` can panic. Combined with the fact
that the registration is global to `eflame` rather than per-costume - so a mistake
would reach the vanilla c00-c05 slots - this is handback point 5. I am not running
it.

Fixing it would mean vendoring smashline to correct the constant, which this
project's `Cargo.toml` rules forbid (no `[patch]`, git deps only, revisions pinned),
or a raw-offset Skyline hook, which is handback point 3. **Projectiles are blocked
pending a decision from the user.** f-air and u-air stay body-only aerials.

### The sword: removed on c06/c07, 0.5.0

The user confirmed the sword "follows me around", i.e. it appears during ordinary
play and not only during specials. The cause is structural: 42 Pyra scripts call
`generate_article(ESWORD)`, and the unported ones are the specials, the Final,
`CliffAttack`, `SlipAttack`, `VisualScene01` and the win/lose poses. Overriding
each is both a lot of work and wrong, because the specials are Pyra's until
phase 4 and need the sword's article to exist.

`build.py` now has `hide_esword(slot)`. The sword skeleton is 8 bones under a
`Root` whose transform is the identity matrix, so zeroing `Root`'s 3x3 basis
collapses every child to the origin and the meshes render degenerate. One asset
change reaches every spawn site at once, the article still exists so Pyra's
generate/remove calls are unaffected, and it uses the file name `esword/c06` that
Pyra already has, so the "never introduce a new file name" rule still holds.

Only c06 and c07 are written. `fighter/eflame/model/esword/` in the output contains
`c06` and `c07` and nothing else, so vanilla c00-c05 keep their sword.

Known trade-off: Pyra's side-B and up-B will now swing an invisible sword on
c06/c07 until phase 4 replaces them with Judge and Fire. That is the correct
interim state - a G&W with a visible Pyra sword is worse than a G&W with an
invisible one.

### 0.5.0 installed

    ultimate/mods/pyra_gamewatch_reskin/   version 0.5.0
      + fighter/eflame/model/esword/c06/  (8 files, Root basis collapsed)
      + fighter/eflame/model/esword/c07/  (8 files, Root basis collapsed)

763 files total, up from 717. `diff -rq` against the built tree is clean. The
plugin NRO is unchanged from 0.4.0 (`83b42b93...`) because this is an asset-only
change. Backup of the whole 0.4.0 mod tree: `sd_backups/2026-09-29_before_pgwr_0.5.0/`.

### Still undiagnosed

The "weird model stuff" and the duplicate G&W. The screenshots the user took on
the Switch did not reach the workspace and no attachment arrived, and this
environment has no image viewer, so they could not be inspected even if they had.
The dormant-partner hypothesis is still untested; the down-B test from run 2's
report is still the decisive one.

### Verified vs built

**Console-verified:** the costume gate (run 3), and the 0.1.0 assets (run 1).
**Built, never run:** the sword removal in 0.5.0, everything in 0.4.0's rapid-fire
fix, and the duplicate diagnosis.

### Next console test

1. **The sword.** Walk, jab, use every special. No sword should ever be visible on
   c06/c07. Check vanilla Pyra c00-c05 *still has* her sword - that is the
   regression this change could cause.
2. **The duplicate.** Spawn as c06, press nothing, then down-B. Does the second
   figure become Mythra?
3. Re-confirm vanilla Pyra, Mythra and real G&W are untouched.

### Open decisions for the user

- **Projectiles are blocked** (see above). Either accept f-air/u-air as body
  aerials, or authorise vendoring smashline to correct the name table, which
  breaks the project's pinned-dependency rule.
- Phase 3 (stats) is untouched and is why he still does not feel like G&W.

---

## Claude review, 2026-09-29: read this before continuing

The user checked 0.5.0 on the console and sent 9 screenshots
(`sd:/emuMMC/RAW1/Nintendo/Album/2026/09/29/`, 01:54 to 01:55). Their words: it
somewhat works but looks really weird, projectile moves don't work, and specials
are completely untouched. **New priority from the user: specials and animations
first. Stats and params are not important right now; park phase 3.**

### 1. The "duplicate G&W" is solved, and it was not the partner

G&W's body model holds all of his props and alternate-pose silhouettes: 98 meshes
(`flagman*`, `judge*`, `No1M`–`No9M`, `sheff*`, `fireattack*`, `LHammerM`/`RHammerM`,
and so on). His clips have on/off tracks for only 94 of them. The other four
(`LHammerM`, `RHammerM`, `flagman1M_FLIP`, `flagman2M_FLIP`) are hidden by his native
code through visibility groups, which Pyra's fighter never sets. So they were drawn
permanently. `flagman*_FLIP` is a whole G&W silhouette holding the "1" and "2" signs,
which is the "second G&W" in every screenshot. The being-thrown clips (`e01thrown*`)
have no visibility group at all, so they drew all 98 meshes stacked (screenshots at
04:36 and 04:23).

The `DIVER` partner hypothesis was wrong. Drop it; no model-layout change is needed.

**Fixed in 0.5.1** (assets only, by Claude): `build.py` has a new `complete_visibility()`
pass that gives every G&W mesh an explicit track in every clip. Missing tracks are
filled with `False`. Clips with no visibility group get the idle clip's full state.
The `a00itemhand*` layers are skipped. It asserts full coverage after saving. It is
built in `mod_output/`, **not yet installed or console-tested**.

Consequence for the port: any move that needs one of those four meshes (for example,
Judge's hammer) must turn it on explicitly with `ModelModule::set_mesh_visibility`,
or by editing the clip's visibility track in `build.py`. G&W's `VisibilityModule::set_int64(hand/head/rhand…)` group
calls in the dumps probably do nothing on `eflame`: the groups are defined for G&W,
not Pyra. That is unverified, so check it with one move. If they are no-ops, translate
the group states into mesh lists (from G&W's own clips, which show which meshes each
state uses).

### 2. Projectiles are NOT provably blocked; your clone_weapon analysis used the wrong plugin

`smashline_clone_weapon` runs inside the **installed** `libsmashline_plugin.nro`, not
in the crate you compile against. The installed plugin (SHA-256 `5f4091ee…`) is
the 13.0.4-corrected build from `mod_files/mgw_standalone/smashline_1304/`. It is
byte-identical to `mod_files/mgw_standalone/target-smashline/.../libsmashline_plugin.nro`,
and its `create_agent.rs` has `LOWERCASE_WEAPON_NAMES` at **`0x5185bd0`**. The
`+0x1000` displacement you found is real in upstream `be3ef30`, but that build is
not what runs on the card. Your own evidence (`breath` → 110, `normal_weapon` → 126
under `0x5185bd0`) shows the installed table works.

So `clone_weapon` is untested, not unworkable. Before using it, read
`smashline_1304/src/api.rs:304` and `src/cloning/weapons.rs`. Note that
`original_article_id` is used as an index into the **weapon-name table**, so what it
wants is a weapon kind, not an article index. Confirm that from the source first.
Registration is global to `eflame`, but vanilla Pyra never generates the new
article id, and only our gated scripts do. So this is a risk to test for, not a
reason to stop.
Do not rebuild or replace the global smashline plugin without handing back.

### 3. What to do now, in order

1. **Install 0.5.1 when the user asks, then run the visual test.** Idle, walk, every
   attack, being grabbed and thrown by a CPU: no signs, no hammer, no second G&W.
   Ask the user which moves still look wrong, and get a screenshot of each.
   Everything left after 0.5.1 goes on an "animation bugs" list, each item tied to a
   motion kind and a clip.
2. **Side-B Judge.** It needs no article: the hammer (`RHammerM`), the judge poses
   (`judge1M`–`judge4M`, `_f` variants) and the number cards (`No1M`–`No9M`, `_f`) are all body
   meshes. **Checked by Claude:** in G&W's own motion list, all nine `special_s_1`…`_9`
   point to `d01specials.nuanmb`, and all nine `special_air_s_*` point to
   `d01specialairs.nuanmb`. *Superseded by the NO SHORTCUTS section:* build Judge as
   custom statuses with G&W's own nine motion kinds, not inside Pyra's `special_s`.
3. **Up-B Fire.** Movement and hitbox first, with the parachute and fire poses as body
   meshes. The trampoline (the `rescue` article) comes later, via clone_weapon.
4. **clone_weapon, one article.** Start with Chef's `food` (neutral-B) or f-air's
   `bomb`. Log the id `clone_weapon` returns and what `generate_article` does with it.
   Check that vanilla Pyra c00–c05 still work in the same session.
5. **Neutral-B Chef**, then **f-air bomb**, **up-air breath** and the jab/down-smash
   `normal_weapon` prop, all on the path that step 4 proved.
6. Down-B stays the vanilla swap. Stats and params: parked.

### 4. Updated hand-back points

Keep the original list, with these changes:
- Remove "clone_weapon or the param-config route is unworkable" as an automatic stop.
  Hand back only if the one-article test (step 4) crashes, or breaks a vanilla slot.
- **Planned checkpoint:** Judge and Fire working on the console, plus the step-4 result.
- Still stop before any raw-offset hook, any new file name or motion kind, or
  rebuilding the global smashline plugin.

---

## NO SHORTCUTS: the user's standard, 2026-09-29. This overrides everything above.

The user, clarifying: *"we for example don't try to squeeze stuff into existing states
where they don't really belong or try to call stuff from other characters, instead we
make new custom states or copy over what we need from other characters."* **The user
does all the console testing.** No trace recorder, and no test tooling on the Switch.

What this means in practice:

1. **G&W's moves get G&W-shaped structure.** Where G&W has a status, motion kind or
   script that Pyra doesn't, create a **new custom status** on the gated `eflame`
   agent. The installed smashline (`smashline_1304`, `create_agent.rs:738-771`)
   registers status ids beyond the vanilla table and grows it (`max_new`), with the
   same per-costume filter as ACMD. Give each one G&W's own **motion kinds** and
   **G&W's own clip names**. Don't reuse a Pyra status or motion kind just because it's
   free and roughly the right shape. Common statuses that every fighter shares (walk,
   jump, attack_s3, and so on) aren't Pyra's, so using them is correct.
2. **Copy, don't reference.** Whatever G&W needs is copied into this mod, owned by
   `eflame` c06/c07, and driven by our code: clips, props, article models, effects,
   sounds, params and status logic (ported from the dumps). At runtime nothing calls
   into G&W's lua2cpp code, and nothing depends on G&W's banks or agents being loaded.
   For articles that means `clone_weapon(..., use_original_code = false)`, with every
   weapon script (ACMD and statuses) ported by us, and the article's model copied under
   `eflame`. `use_original_code = true` borrows G&W's code, so it's out.
3. **No stand-ins.** No Pyra sounds for G&W sounds, no body hit instead of the bomb, no
   hiding a Pyra thing instead of replacing the status that makes it. A line from the
   dump that can't be ported yet is a to-do, not a drop.
4. **When the proper route needs something reserved** (a raw-offset hook, rebuilding the
   global smashline plugin), hand back with the evidence. Don't pick a cheaper route.

### Prerequisite: adding files and motion kinds

Rule 1 needs new motion-list entries and new file names on c06/c07. The earlier "never
add a new file name" rule came from one failure: motion entries pointed at files that
existed nowhere. It was never tested with ARCropolis' proper file-addition route (`config.json`,
`new-dir-files` and the related keys; the old clone packs in
`sd_backups/2026-09-29_before_pyra_gw_reskin/ultimate/mods*/*/config.json` used it). **Do this
first:** add one G&W motion kind with its own clip under its G&W name to
`eflame/motion/body/c06`, play it from a custom status, and have the user confirm it on the
console. Record the result in `.agents/rules/move_replacement_guide.md`. Everything below
depends on it. If it cannot work, hand back.

### What currently violates this, and what replaces it

| # | Now | Replace with |
| - | --- | --- |
| 1 | **Pyra's motion kinds carry G&W clips** (`build.py` overwrites her clip files; fallbacks like `special_n_*` → `special_n`, `attack_100_start` → `attack_100`, and `wait` for the rest). | Common motion kinds keep G&W's clip under the common kind. G&W-only kinds (`special_s_1`…`_9`, `special_hi_open/close`, `special_n`, `attack_100`, `final_*`, and so on) are added as their own entries with G&W's clip names. Pyra-only kinds are unreachable on c06/c07 once her statuses are replaced; they shouldn't need a G&W clip at all. |
| 2 | **R5: G&W's `Attack11` scripts registered under Pyra's `Attack12`/`Attack13`**, plus Pyra's `Attack100Start` kept. | G&W's jab structure: Attack11 → Attack100 → Attack100End, with no 12/13 and no start phase. Stop the combo from entering 12/13 on c06/c07 by the mechanism G&W uses (his params and status flow), not by pointing the extra states at jab 1. |
| 3 | **R1: articles dropped** (jab and down-smash `normal_weapon`, f-air `bomb`, u-air `breath`, and later `food`, `rescue`, and so on). | Copied articles as described in rule 2. |
| 4 | **R2: G&W sounds replaced by Pyra's.** | G&W's sounds copied into a bank that c06/c07 load, under the names his scripts use. Pyra's voice must not play (G&W has none). |
| 5 | **G&W effects** not available to `eflame`. | G&W's effects copied into an effect file that c06/c07 load. The effect names his scripts use have to resolve. |
| 6 | **R3: raw-hash notify dropped; R6: G&W work-id writes dropped.** | Find out what each does, and reproduce it: work state in plugin-owned storage per entry, the notify's effect in our status code. |
| 7 | **`CaptureDamageLw` left as Pyra's.** | Ported. Declare the missing binding from its symbol if necessary. |
| 8 | **Visibility: Claude's 0.5.1 pass** writes `False` tracks into G&W clips, and **`hide_esword`** collapses the Aegis model. Both are workarounds. | G&W's visibility groups (`hand`, `head`, `rhand`, `lhand`, `zzz`, `panel`…) reproduced in the plugin, so the ported `set_int64`/`set_default_int64` calls work as on G&W; the clips then go back to being unedited copies. The Aegis never spawns on c06/c07, because every status that generates it (specials, cliff attack, slip attack, entry, win) is replaced by G&W's. Remove `hide_esword` once that's true. Likewise, the grafted Pyra bones exist only for leftover Pyra scripts; remove them when none remain. |
| 9 | **Specials: all four are Pyra's.** | Judge: custom statuses with the nine `special_s_N` / `special_air_s_N` kinds (all of them point to `d01specials.nuanmb` / `d01specialairs.nuanmb` in G&W's own list), the number chosen by G&W's rules (odds, no repeat), and each number's own ACMD. Fire: custom statuses plus the `rescue` article and the parachute fall. Chef: custom status plus `food`. **Down-B stays the vanilla swap (the user's design).** |
| 10 | **Stats, params, hurtboxes, model scale** are Pyra's. | G&W's, copied. Lower priority for now, per the user, but required. |
| 11 | **Final Smash, taunts, entry, win poses and results screen, Kirby's copy ability, portraits, stock icon, HUD, name, announcer, CPU AI** are Pyra's. | G&W's, copied. |
| 12 | **`visual_scene_01/02` (the swap cutscene)**. | Not a violation, a design question: G&W has no equivalent. **Ask the user.** |

### Order

The file and motion-kind prerequisite first. Then specials and animations, as the user
asked: 1 and 2, then Judge, Fire and Chef (9), with each move's articles, effects and sounds
(3, 4, 5) done as part of the move. Then 6, 7 and 8, then 10 and 11.

**Hand back when:** Judge and Fire are complete by the standard above and the user has
confirmed them on the console. Also hand back at any stop point in the earlier lists, or if the prerequisite fails.

---

## Claude 0.7.0: normals pass. READ BEFORE TOUCHING build.py OR THE GENERATORS

Full write-up: `REPORT_0.7.0_NORMALS.md`. Changes that affect you:

* **Do not use new file names.** `add_gw_motion_kinds`/`NEW_MOTION_KINDS` (0.6.0) are gone. Your lesson
  "new file names do work" was offline-only and contradicts the console result in `HANDOFF.md` (Monkey
  Flip: entries naming mod-shipped files that did not exist in the base folder played the wrong clip;
  existing names worked). Correction logged in `.agents/rules/move_replacement_guide.md`. eflame c06/c07's
  motion list is now **G&W's whole list**: every G&W kind exists (`special_s_1`..`_9`, `_l`, air versions,
  `special_hi_open/close`, `special_lw_*`, `final_*`), and the 20 clips whose names eflame lacks are stored
  under spare eflame names (see `build_motion`, ALIAS notes, and `clips_aliased` in `build-record.json`).
  You refer to motion **kinds** only, so nothing in your status code changes; `judge.rs` still works.
* Pyra-only kinds (her specials, final, swap, entry, visual scenes) are kept with **G&W stand-in clips**.
  Down-B's swap kinds must stay. Your own Pyra-only special statuses are gone once you replace them.
* `generated/common.rs` (from `tools/gen_common.py`) now overrides 388 G&W scripts and empties 50 Pyra
  ones for every non-special motion. **Your special/final scripts must not collide with these**: the
  generator skips suffixes starting `special`, `final`, `entry`, `visualscene`. Do not edit `common.rs`;
  change the generator. `gen_acmd.py` gained rules R14-R21; `--check` still passes for your four groups.
* `expression_vl.prc` now carries G&W's mesh-visibility groups (per fighter). Judge's `panel` group calls
  work through it. New rule for your specials: **check a script's `VisibilityModule::set_int64` calls against
  the tables in `param_visibility_data_body`** rather than assuming a group exists.
* Sounds are still Pyra's (183 scripts), and item-handling scripts are listed unported. Both are inventory
  items, not decisions.
* Up tilt / up smash L/R variants, the jab chain and the article props need **custom statuses / params**,
  which is your area. Suggested next after the user's test of 0.7.0: those, then Fire (up-B).
* Build tooling: `scratch/py312/python.exe build.py`, then `tools/gen_common.py`, then `build-plugin.sh`
  (the script stages the NRO). `tools/prc.py` reads/writes `.prc`; use it, not `pyprc`, to edit params.

---

## NEXT TASK (user, 2026-09-29): G&W's props ("weapons") do not appear

**Console result for 0.7.0:** legs fixed, animations look normal. What is still missing is what the user
calls G&W's weapons: the fishbowl, the stool, "etc." This is your task now, ahead of up-B.
The NO SHORTCUTS rules apply as written.

### Diagnosis (Claude, from the dumps; nothing here is console-verified)

These props are not body meshes. They are one **article**, `normal_weapon`, and the port drops every
reference to it (rules R1, R6, R21; each drop is listed in the `GEN-NOTES` header of the generated file).

* Assets: `export/fighter/gamewatch/model/normal_weapon/c00..c07` (33 meshes) and
  `export/fighter/gamewatch/motion/normal_weapon/c06` (own `motion_list.bin`, `update.prc`, 10 clips).
  **Each clip already selects its prop by its visibility tracks**, measured:

  | article motion | clip | prop shown | owner script that drives it | `NORMAL_WEAPON_KIND_*` set |
  | --- | --- | --- | --- | --- |
  | `attack_11`, `attack_100`, `attack_100_end` | c00attack11/100/end | `KiriM1-15` (spray) | Attack11, Attack100, Attack100End | SPRAY |
  | `attack_s3` | c01attacks3s | `chairM` (stool) | AttackS3 | CHAIR |
  | `attack_lw3` | c02attacklw3 | `ManholeM` | AttackLw3 | MANHOLE |
  | `attack_air_n`, `landing_air_n` | c05attackairn / landingairn | `TankM`, `Fish*`, `Splash/OverflowM` (fishbowl) | AttackAirN, LandingAirN | TROPICALFISH |
  | `attack_air_b`, `landing_air_b` | c05attackairb / landingairb | `Kame`, `Head*`, `*FootM` (turtle) | AttackAirB, LandingAirB | TURTLE |
  | `appeal_lw` | j01appeallw | spray | AppealLwL/R | SPRAY |

* Owner-side calls: `ArticleModule::generate_article(NORMAL_WEAPON)`, `change_motion(NORMAL_WEAPON, <motion>)`,
  `remove`/`remove_exist`, `IS_EXIST_ARTICLE`, `SET_RATE_ARTICLE_V` (landing), and
  `WorkModule::set_int(KIND, FIGHTER_GAMEWATCH_INSTANCE_WORK_ID_INT_NORMAL_WEAPON_KIND)`. G&W's article id 5 and
  work id `0x100000BD` do not exist on eflame, which is why they were dropped.
* There is **no ACMD dump for `gamewatch_normal_weapon`** (`lua2cpp_gamewatch/` has folders for bomb, breath,
  food, octopus, oil, parachute and rescue, but not this one). Its behaviour (following the hand, reading the kind, any
  hitbox) is native code in `export/prebuilt/nro/release/lua2cpp_gamewatch.nro`. Decompile its statuses with the
  Ghidra workflow used before (outputs in `references/mythra_gamewatch_feasibility/ghidra_scripts__*.c`) and port
  them; do not guess.
* **Separate but related: down-attack / slip-attack hammers.** `LHammerM`/`RHammerM` are body meshes that no G&W clip
  animates. His scripts ask for `rhand_hammer`, which is **not** in his `param_visibility_data_body` table (the
  `rhand` group has only `rhand_none`), so native code shows them. Claude's 0.5.1 visibility pass forces them to
  `False` in every clip, so on eflame they can never appear. Find the native mechanism and reproduce it; the forced
  `False` for those two meshes is part of the workaround to remove (handoff item 8).
* The up-smash helmet (`HelmetM`, `helmet` group) *is* a body-mesh group and should work since 0.7.0. Ask the user
  to confirm it, and don't assume.

### How to do it properly

1. **Resolve file addition first.** A cloned article needs its own model and motion folders under `eflame`
   (for example `fighter/eflame/model/<name>/c06`), and those are file names eflame has never had. Console evidence so far
   (Monkey Flip, `HANDOFF.md`) says mod-shipped *new clip names inside an existing motion list* did not load. It
   did **not** test ARCropolis' explicit file-addition route (`config.json`: `new-dir-files` / new directories; the old
   clone packs in `sd_backups/2026-09-29_before_pyra_gw_reskin/ultimate/mods*/*/config.json` used it). Build a
   minimal isolated experiment for that route, and have the user run it before anything depends on it. Record the result
   in `move_replacement_guide.md` either way. **If new files cannot be made to load, hand back**; do not squeeze the
   article's assets into an unrelated eflame article folder.
2. **Clone the article as eflame's own.** `smashline::clone_weapon("gamewatch", <weapon kind>, "eflame", <new name>,
   false)` on the installed `smashline_1304` build (its weapon-name table is the corrected `0x5185bd0`). Read
   `smashline_1304/src/api.rs:304` and `src/cloning/weapons.rs` first: confirm that the second argument is a weapon kind,
   how the clone's resources and model path are resolved, and whether its scripts can be costume-gated. Also read
   `mod_files/mgw_standalone/DIAGNOSIS.md`, which covers resource-global and `FilesystemInfo` crashes from the same
   plugin family. `use_original_code = false` means you port every weapon status yourself (step 3).
3. **Port the article's statuses** from the decompiled `lua2cpp_gamewatch.nro` code as smashline weapon statuses
   on the cloned agent. Copy its model, `motion_list.bin`, `update.prc` and all 10 clips (the clip names are its
   own; its visibility tracks already choose the prop, so do not run the visibility pass over them).
4. **Put the owner's calls back.** Replace R1/R6/R21's drops for `NORMAL_WEAPON` with a translation in the
   generator: G&W's article id becomes the cloned id, and the kind work-int becomes plugin-owned per-entry storage
   that the ported weapon status reads. Change `gen_acmd.py`/`gen_common.py` and regenerate; never hand-edit
   `generated/*.rs`. Keep R1/R21 for the other G&W articles (bomb, breath and so on), which are later items.
5. **Hammers:** find the native code behind `rhand_hammer`, reproduce it on c06/c07, and drop the forced `False`
   for `LHammerM`/`RHammerM` from `complete_visibility` once it works.

### Console test to hand the user (write the exact steps and expected `[PGWR]` lines)

Pyra c06 and c07: jab and rapid (spray), f-tilt (stool), d-tilt (manhole), nair and its landing (fishbowl), bair
and its landing (turtle), down taunt (spray), up smash (helmet), down attack / slip attack (hammers). Then the
controls: vanilla Pyra c00-c05, Mythra, and real G&W with his own props.

### Hand back when

* the props work on the console for both slots, and the controls are unchanged (planned checkpoint); or
* the file-addition experiment fails; or
* `clone_weapon` cannot be made costume-safe, or it needs a raw-offset hook or a rebuilt global smashline plugin; or
* the native `normal_weapon` statuses cannot be decompiled well enough to port without guessing.
