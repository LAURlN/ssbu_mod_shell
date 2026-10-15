# Architecture assessment — 2026-09-28

Written after the dump outage was fixed. It re-evaluates the approach against the
user's stated goal and splits the remaining work between a capable model and
cheaper models. `HANDOFF.md` still describes the loader checkpoint;
`HANDOFF_WEAK_MODEL.md` is the task list for a cheaper model.

## The goal, as stated by the user

1. A selectable Pyra/Mythra clone pair, coexisting with the originals, 8 costumes.
2. It must **play and feel exactly like the original**, not an approximation.
3. It must be **fully editable**, eventually to the point of two completely
   original characters that switch between each other. Copy as much as possible.

(2) and (3) pull in different directions. Copied/relocated machine code is exact but
not practically editable. Hand-rewritten code is editable but only approximately
right unless it is *proven* equal. The plan below gets both, in that order.

## Findings

### What exists

| Asset | State |
| --- | --- |
| Data copies (`editable/`) | 9,234 files, 8 costumes, motion lists retargeted. Reusable as is. |
| Dumps | Complete for current needs (0 missing), live copies byte-identical, game 13.0.4 = the version of our main image and the version Clone Engine targets. |
| ACMD (game/effect/sound/expression scripts) | Already in smashline Rust: `SSBU-Dumped-Scripts-main/smashline/lua2cpp_{eflame,elight,element}`, ~1,900 files. The dump author warns some contain errors. |
| Status scripts (the per-state logic: pre/main/end/exec…) | **Not decompiled anywhere in this workspace.** Compiled inside `lua2cpp_eflame/elight/element.nro`. |
| Native main-executable code | 22 directly imported functions (`FighterSpecializer_EFlame/ELight`, `FighterElementLinkEventChange`, sword/diver weapon specializers) and 17 classes (2 fighters, 15 weapons) with 24–28 character-specific vtable slots per fighter. Inventoried by Astra; not analysed. |
| Clone Engine 0.4.0-beta.1 (`upstream/clone_engine`) | Registers a new fighter kind on a vanilla base, copies the base's class/vtable, routes files, params, effects, sounds, UI, articles, Kirby; per-clone vtable overrides (`clone_engine_vtable_override_v2`); kind-aware shared hooks (`clone_engine_shared_hook_v2`); smashline scripts by clone name. 13.0.4 only. |
| Earlier pair attempt (`mod_files/mgw_standalone`, p1–p16) | Same idea on Clone Engine (Mythra + hidden partner). **Never ran on hardware without crashing.** The final crashes were in Mythra's articles resolving the vanilla body model (`main+0x35c23a8`, file `0x34e65`) and a motion-bind state skip at `main+0x49748c`. p16 was never tested. Its `ARCHITECTURE.md` documents that Clone Engine has one custom kind per player entry, so a two-form pair breaks its identity, param and article lookups. |

### What this means

- **Clone Engine is the right base, but it does not support this character yet.**
  It has no transforming pairs, and even a single Mythra clone has not loaded.
  Pyra/Mythra are among the hardest possible bases: two fighters per entry, a
  native link/swap event, and 13 articles, some of which use the owner's body model.
- **Exactness should come from running the original code, not from rewriting.**
  If the clone kind runs the vanilla vtable and the vanilla lua2cpp scripts, it
  is exact by construction, as long as every place the game checks "is this
  Pyra/Mythra?" also accepts the clone. A raw scan of `main` finds ~150 immediate
  comparisons against kinds 90/91, but that is no more than neighbouring kind
  numbers (noise). The real kind-dependent sites have to be found by proper
  analysis and, above all, by on-console comparison.
- **Editability then comes layer by layer, each one proven equal first.**
  ACMD → smashline under the clone's name. Status scripts → smashline statuses
  under the clone's name. Native class methods → per-clone vtable overrides. Main-
  executable specializer code → kind-checked shared hooks. Each replacement must
  produce *identical frame traces* to the vanilla fighter before anyone edits it.
  After that, edits are deliberate and everything else stays exact.
- **Astra's relocation plan is parked, not deleted.** Relocating machine code gives
  independence but not editability, and it is the most error-prone path.
  The renamed private modules (`native/modules`) remain useful as an option if
  the clone must stop depending on the vanilla `lua2cpp_*.nro` files. They are not
  on the critical path.

## The fidelity guarantee: differential traces

"Feels exactly the same" becomes a test, not an opinion:

1. A **trace plugin** logs, per frame, for each fighter of interest: frame number,
   kind, status kind, situation, motion hash + frame + rate, position, per-energy
   speeds (kinetic energies), LR, damage, hitlag/shield stun, active hitbox
   parameters (id, damage, angle, KBG/BKB, size, offsets), hurtbox state,
   article count/kinds, and a chosen set of WorkModule ints/flags/floats.
2. **Identical inputs** via recorded-input playback in Training mode, from a fixed
   start position and seed. The UltimateTrainingModpack's input recording and
   playback is the first candidate; verify it plays back frame-exact before relying on it.
3. A **PC-side diff** of vanilla vs clone traces. Pass = zero differences except the
   kind/identity fields. Any difference names the first frame and field that diverge.
4. A **scenario library**: every move grounded/aerial, every special incl. swap in
   both directions from each posture, Final Smash, ledge, shield, grab/throws,
   items, respawn, Kirby copy. It is a checklist that grows, and each entry is a recording.

Every later change (engine fix, ported ACMD, ported status, vtable override) must
pass the traces for the scenarios it affects. Without this, "exact" cannot be claimed.

## Milestones

| # | Milestone | Done when |
| --- | --- | --- |
| M0 | Trace plugin + PC diff tool + input playback proven | Vanilla Mythra vs vanilla Mythra (two runs) diff to zero; one deliberate param change shows up in the diff |
| M1 | Single Mythra clone loads (fix the p1–p16 crash chain) | Clone Mythra finishes a match; originals unaffected |
| M2 | Single-form clone exact | Clone Mythra (swap disabled) traces equal vanilla for all non-swap scenarios; same for Pyra |
| M3 | Pair support in Clone Engine | One CSS entry spawns both clone forms; the swap works in both directions; traces equal vanilla, including swap scenarios, damage/stocks, respawn, results |
| M4 | Ownership layer | ACMD then statuses moved into the clone's smashline crate one by one, each trace-verified; the vanilla behaviour is still what runs |
| M5 | Editing | Deliberate edits; the trace suite then documents exactly what changed |

M1–M3 are the hard part and need a capable model. M4 is high volume and suits
cheaper models *because* M0 makes every piece mechanically checkable.

## Who does what

**Capable model only** (wrong answers here cost console sessions and are hard to notice):
- M1 crash chain, M3 pair support inside Clone Engine (entry → two objects,
  identity/param/article routing, the native link event, swap state transfer).
- Finding kind-dependent code in `main` for 90/91/element and deciding how
  each is made clone-aware.
- Decompiling status scripts from the lua2cpp NROs, and designing the port pattern.
- The trace plugin's native reads (hitbox/kinetic structures) and anything with offsets.
- Reviewing cheaper-model output before it goes on the console.

**Cheaper models** (every task needs an automatic check; see `HANDOFF_WEAK_MODEL.md`):
- PC-side trace diff tool and its tests (no console needed).
- ACMD inventory and porting into a feature-gated smashline crate, with compile checks
  and a mechanical source-equivalence check against the dump.
- Status-script transliteration *after* a capable model has produced decompilations
  and one reviewed worked example, each gated by traces.
- Data work: costume/UI/text/param rows, pack layout validation, hash manifests.
- Scenario recording checklists, log/trace triage, report upkeep.

## Risks

- Clone Engine is a beta written by one team; pair support means maintaining a
  fork. Keep changes as a documented patch set (as `mgw_standalone` did).
- Input playback may not be frame-exact across runs (RNG, stage hazards). Use
  Training mode, a hazard-free stage and a fixed seed, and prove determinism in M0 first.
- Some Pyra/Mythra behaviour (the Aegis-sword articles, Foresight, Final Smash
  cinematics) is native and may have per-kind lookups that only show up in rare scenarios.
  The scenario library has to cover them explicitly.
- The earlier p1–p16 evidence is the best starting point for M1; read
  `mod_files/mgw_standalone/DIAGNOSIS.md` before touching the engine.
