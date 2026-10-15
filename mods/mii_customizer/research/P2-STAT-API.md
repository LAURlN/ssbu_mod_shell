# P2-STAT-API - supported runtime APIs for per-instance walk speed and weight

Task: `P2-STAT-API`. Worker: Space Bunny Alpha. Date: 2026-10-04.
Prompt: `prompts/P2-STAT-API.md`. Coordinator review:
`research/COORDINATOR-2026-10-04.md`.

**One question.** For `walk_speed_max` and `weight`, is there a supported runtime
API that overrides the value for **one** Gunner instance independently of another
Gunner in the same match? This is a source-based assessment. No hook was built,
no offset was guessed, no game was run.

Evidence tiers: **B** offline measurement of local files; **C** pinned third-party
source; **D** hypothesis. **No tier A.** Exact inputs, hashes, commands and the
failing/passing checks are in `evidence/P2-STAT-API/PROVENANCE.md`.

---

## 1. Verdict up front

| question | answer |
|---|---|
| Is there a per-object accessor/callback for these two parameters? | **Yes, one shape of them.** The `WorkModule` param accessors take the calling battle object and are already hooked per-object in a sibling mod. **C** |
| Is the owner of the value available? | **Yes.** The hook's first argument is the `BattleObjectModuleAccessor` of the fighter asking, from which kind, category and per-object work ints are readable. **C** |
| Can two Gunners be told apart at that point? | **Not by these two parameters.** The one demonstrated discriminator is a per-object work int that stands for *costume*, not for *saved Mii*. Separating two Gunners by saved-Mii identity is unresolved. **D** |
| When can values be cached? | A runtime-cached param layer is documented in the binding with a recalculation entry point, but that entry point's own name is flagged as assumed by its author. **D** |
| What resets on stock loss / respawn / object destruction? | **Unknown. No pinned source says anything about it for these two parameters.** |
| Is supported per-instance scoping demonstrable from sources? | **No — reported unresolved.** The smallest missing native question is named in §7. |

**A global PRC replacement is not per-instance**, and nothing below relies on one.
`FighterParams` is a singleton table of 94 per-kind rows indexed by fighter kind
(`skyline-smash/src/params.rs`, `params/fighter_param.rs`); writing row 82
changes Gunner for everybody in the match. That route is excluded by the prompt
and is not proposed.

---

## 2. The two parameters, re-derived

The catalogue's records were not taken on trust. Re-decoding the pinned
`fighter_param.prc` with the workspace's own reader gives, independently:

| parameter | Hash40 | type | Gunner row 82 default | f32 bits |
|---|---|---|---|---|
| `weight` | `0x0607cd5541` | float | `104.0` | `0x42d00000` |
| `walk_speed_max` | `0x0ee2ec2860` | float | `1.0` | `0x3f800000` |

94 rows; exactly one row carries `fighter_kind == hash40("fighter_kind_miigunner")`
and it is at index **82** (`B`, reproducing P1-DATASET §4). A pinned third-party
field table in the old mod repo independently lists the same Hash40 for both
names at row offsets `0x80` and `0x10` of a `0x628`-byte row (`C`).

So the file side is settled: both are plain `float` entries in the Gunner row of
the **common, per-kind** `fighter_param` table. What is not settled is where the
engine reads them from at runtime, and whether that read site is per-object.

---

## 3. API / signature / provenance

| # | symbol | signature (as declared) | what it is | provenance |
|---|---|---|---|---|
| D | `WorkModule::get_param_float` | `extern "C" fn(this: &WorkModule, param_object: phx::Hash40, param_name: phx::Hash40) -> f32` at vtable offset `0x270` | **declaration only.** The impl entry `get_param_float_impl` sits at `0x268` | smash-rs `ddacc5e`, `src/app/modules/work.rs` |
| D | `WorkModule::get_param_int` | same shape `-> i32`, `0x250` (`_impl` at `0x248`) | declaration only | same |
| D | `WorkModule::set_customize_no` | `fn(this: &mut WorkModule, variant: i32, move_no: i32)` at `0x278` | declaration only; documented as "only really used by mii fighters and joker … for their specials" | same |
| D | `WorkModule::recalculate_params` | `fn(this: &mut WorkModule, _unused: u64, is_abnormal: bool)` at `0x280` | declaration only; documented as "recalculates runtime-cached params based off of a stat change", sends event `0x31` | same |
| D | `lua_bind::WorkModule__get_param_float_impl` | `(BattleObjectModuleAccessor*, u64, u64) -> f32` | the lua2cpp marshalling of D's first symbol, once, no second overload | skyline-smash `315e4e8`, `src/cpp.rs` |
| A | pgwr's `param_float` | `unsafe fn(boma: *mut BattleObjectModuleAccessor, parent: u64, child: u64) -> f32`, installed by `#[skyline::hook(replace = WorkModule::get_param_float)]` | **a real implementation** of D, per object | old mod `src/pgwr/plugin/src/params.rs`, compiled into the pgwr plugin |
| B | clone engine per-object param object | pointer at `accessor + 0x2758`, `0x1b60` bytes, written after accessor init keyed on the accessor's entry id | a **per-battle-object** param store; does **not** list either parameter | old mod vendored clone engine |
| C | `smashline::WHITELISTED_PARAMS` | `RwLock<BTreeMap<i32, Vec<Hash40>>>` | the framework's own override registration, keyed by **fighter kind only** | smashline `be3ef30`, `src/params.rs` |

**Declaration is not implementation.** Rows marked D are bindings: a signature and
an offset into a vtable. None of them is a body, and none of them was observed
running. Row A is the only entry in this table that is implemented code, and it
is implemented in the *other* mod, for *its* fighter, on *its* parameters.

---

## 4. Implementation path A - the per-call accessor (the one that matters)

`WorkModule::get_param_float` is called with the asking object's module accessor.
The old mod replaces it wholesale and substitutes a value keyed on
`(parent_hash, child_hash)` **after gating on the object itself**:

1. is the object a fighter at all (`app::utility::get_category`)?
2. is it the target fighter kind (`app::utility::get_kind`)?
3. only then does it return a substituted value, and only for hashes in its table.

That third step is the part this task cares about, and it is the part that is
already **per-instance-capable by construction**: the gate is evaluated per call
against the calling object, not against a global. `walk_speed_max`
(`0x0ee2ec2860`) and `weight` (`0x0607cd5541`) are both in that table today,
because the sibling mod ships G&W's values for its own two fighters.

What path A **does not** give this project:

* **It cannot separate two Gunners.** The only per-object discriminator it uses
  is `FIGHTER_INSTANCE_WORK_ID_INT_COLOR`, which is a costume/colour index. Two
  players using the same Gunner costume share it. A saved-Mii identity is not in
  the gate and no binding consulted here exposes one.
* **It is a call-time substitution, not a stored value.** It changes what a reader
  of that accessor receives at the moment it asks. Whether the engine asks once
  at spawn or every frame is not stated by any source read here.
* **It is not this project's code and not authorised here.** It lives in another
  mod's tree, whose own rules (`mods/ssbu_mod_new/AGENTS.md` §D.22) forbid
  touching framework plugins and the rules for this project forbid runtime
  behavior edits in this batch. It is cited as evidence that the shape works,
  not as a component.

## 5. Implementation path B - the per-object param store (inspected, not usable)

The vendored clone engine demonstrates a genuinely per-battle-object parameter
store: a `0x1b60`-byte param object reached at `accessor + 0x2758`, assembled
from per-fighter copies of six shared `.prc` files, written after accessor init
and keyed on that accessor's own entry id (read from the entry struct at `+0xa8`).
This is the right *shape* for this project: per object, reset on init, no global.

It is nevertheless unusable for these two parameters, for a concrete measured
reason: its curated field table (1238 entries spanning offsets `0x58`–`0x1a88`)
lists **neither `weight` nor `walk_speed_max`**. Both live in the per-kind
`fighter_param` row, not in this per-object object. So path B cannot be pointed at
these two values without first establishing that they are read from the per-object
object at all — which is exactly the open question in §7.

Recorded, not proposed: the clone engine's *other* mechanism swaps the **global**
row pointer around fighter init phases under a mutex. That is a global
`fighter_param` replacement scoped by a call window. The prompt excludes it and it
would not separate two live Gunners anyway.

## 6. The framework's own route is per kind, so it cannot help here

`smashline`'s param override installs a reimplemented `get_param_object` on the
`FighterParamHolder` vtable at construction, and the value list comes from
`WHITELISTED_PARAMS: RwLock<BTreeMap<i32, Vec<Hash40>>>` — an `i32` **fighter id**
key. Every instance of a kind gets the same list. There is no instance key
anywhere in that map. The same file exists locally as a 13.0.4 fork; apart from
one re-verified construction offset (`0x37209b4 + 0x5B0` upstream → `0x37209b4`)
the two files are identical, so the per-kind conclusion holds for 13.0.4 too.

## 7. Unresolved, and the smallest question that would settle it

Per-instance scoping **cannot be demonstrated from the sources available here**.
Stating that plainly is the honest result; the prompt asks for it rather than for
a guess.

The exact smallest native/runtime question:

> **Does the 13.0.4 engine read `weight` and `walk_speed_max` for a fighter
> through `WorkModule::get_param_float` (`WorkModule+0x270`), and if so, how many
> times per life — once at fighter init, or on every use?**

That one question decides everything downstream:

* If it is called per use, a call-time substitution (path A's shape) is a
  sufficient per-instance override and no per-frame state forcing is needed.
* If it is called once at init and the result is cached into runtime state, then
  a call-time hook is not enough, and the work moves to *what the cache is and
  when it is rebuilt* — which is the second question, `recalculate_params`
  (`WorkModule+0x280`) and its event `0x31`.
* Either way the *discriminator* question stands on its own: what per-object value
  identifies a saved Mii at battle time. That is the same identity blocker
  P1-ID has not closed, and it is not a stat-API question.

What would **not** answer it: reading the `.prc` again, grepping dump text,
building a hook, or setting current kinetic speed. Setting kinetic speed is a
different quantity from the parameter and is explicitly out of scope here.

## 8. Proposed future diagnostic (design only; not built, not run)

Purpose: separate a true parameter override from a temporary kinetic change, and
show that the substitution is per object rather than per kind. This is a
**proposal**. The values below are chosen to be unmistakable if the mechanism
works. **They are not declared safe and no range has been measured** — the
catalogue records every safe range as `UNKNOWN` with null bounds, and nothing here
changes that.

**Setup.** Two players, both Mii Gunner, same match, distinguishable only by a
per-object work int the diagnostic sets differently at spawn. Controls:

| arm | Gunner A | Gunner B |
|---|---|---|
| 1 — no-override control | vanilla | vanilla |
| 2 — single-object override | `weight` 104.0 → **150.0**, `walk_speed_max` 1.0 → **1.5** | vanilla |
| 3 — both, opposite values | `weight` **70.0**, `walk_speed_max` **0.5** | `weight` **150.0**, `walk_speed_max` **1.5** |

Arm 1 is the vanilla negative control and must be run in the same build as arms 2
and 3, with the substitution code present but disabled, so a difference cannot be
attributed to the build. Arm 3 is the real test: if scoping is per kind, A and B
come out identical or the change leaks between them; if it is per object, the two
sets stay apart.

**What to log** (values only, no pointer probing):

* at fighter init: object id, entry id, kind, and the substituted
  `(parent, child, value)` triples actually returned;
* the **number and timing** of `get_param_float` calls per life for
  `0x0607cd5541` and `0x0ee2ec2860` — this is the direct answer to §7;
* on stock loss and on respawn: whether the object is re-initialised and whether
  the substitutions are re-applied;
* after each KO: the surviving fighter's values, to expose leakage;
* a vanilla arm-1 log with the same line format, so background noise can be
  distinguished from signal.

**Reading the result.**

| observation | conclusion |
|---|---|
| arm 3 keeps the two sets apart **and** the call log shows repeated reads after init | per-instance parameter override; the hook shape is sufficient |
| arm 3 keeps the sets apart but the call log shows **one** read per life | the value is cached at init; a call-time hook is insufficient; escalate to the `recalculate_params` / event `0x31` question |
| arm 3 shows both Gunners with the same values | scoping is per kind, not per object; the framework route and any global row swap are ruled out |
| walk changes but knockback does not (or the reverse) | a kinetic value was touched, not the parameter; this is the "temporary kinetic change" failure mode and does **not** count as an override |
| arm 1 differs from a stock build | the substitution is not actually gated per object; stop and fix the gate |

Weight must be judged by knockback controls, not by fall speed or floatiness —
the coordinator already corrected that once for this project.

**Rollback.** One build flag; disabling it restores vanilla. No data files, no
save format, no framework plugin.

---

## 9. Limitations

1. **No tier A.** No console, no emulator, no build. Every statement is about
   source text or file bytes.
2. **Source reading is not runtime behaviour.** Nothing here shows the engine
   reads row 82, reads it through the accessor named here, or reads it more than
   once.
3. **One crate's pin is unconfirmed.** `smash-rs` (`ddacc5e`) is present in the
   local cargo cache but is not pinned by the workspace `Cargo.lock` consulted;
   treat its offsets as C-weak. `skyline-rs`, `skyline-smash` and `smashline` are
   pinned by `builds/.cache/pikachu-airb/plugin/Cargo.lock`.
4. **No offsets were derived here.** Every address quoted is copied from a pinned
   source file, with its file named. No instruction bytes were verified against
   the local 13.0.4 `main`; that remains the old mod's job under its own rules.
5. **Caching and reset are unresolved** for these two parameters specifically. The
   existence of a cached layer and of an event is a binding author's doc comment
   (`D`), and `smash-rs` itself marks those names as assumed.
6. **The saved-Mii identity discriminator does not exist in any binding consulted.**
   That is the blocker, ahead of the stat API.
7. **Nothing was extracted, downloaded or installed.** No game file was written
   outside this project's own task folders.

## 10. Next experiment

One thing, in order:

1. **Answer the §7 question offline**, by counting and dating the
   `get_param_float` reads for `weight` and `walk_speed_max` in the local 13.0.4
   `main` — the call sites and their callers, not a hook. If the reads are
   init-time only, everything downstream changes and the diagnostic in §8 is not
   yet worth building.
2. Only then build the §8 diagnostic as a single-flag build with arms 1–3.
3. Identity scoping stays blocked on P1-ID regardless of the outcome above.

Escalation to a premium model is **not** requested: nothing found here needs it.
The open items need measurement.

---

## Summary

- **P2-STAT-API: DONE** (assessment complete; the scoping question itself is
  reported **unresolved**, which is the requested finding).
- **Changed files**, all inside this task's exclusive write paths:
  - `mods/mii_customizer/research/P2-STAT-API.md` (this report)
  - `mods/mii_customizer/evidence/P2-STAT-API/check_stat_api_sources.py`
  - `mods/mii_customizer/evidence/P2-STAT-API/check_output.txt`
  - `mods/mii_customizer/evidence/P2-STAT-API/PROVENANCE.md`
  - `mods/mii_customizer/scratch/2026-10-04_P2-STAT-API/probe_param_row.py`
  - `mods/mii_customizer/scratch/2026-10-04_P2-STAT-API/neg_control.py`
- **No extraction, no dependency installed, no Rust built, no framework or shared
  contract touched, no UI analysis, no layout change, no catalogue change.**
  `STATUS.md`, `CHANGELOG.md`, `CURRENT_INSTALL.md` and other workers' reports were
  not edited. Inputs were read-only.
- **Observed checks:** `check_stat_api_sources.py` **59/59 pass, exit 0**, and a
  second run is byte-identical. Negative control (one perturbed row key) fails
  loudly, exit 1. Independent `.prc` re-decode reproduces 94 rows, the unique
  Gunner row at index 82, `weight` `104.0` / `0x42d00000` and `walk_speed_max`
  `1.0` / `0x3f800000`.
- **Verified (B):** both parameters' Hash40, type, Gunner row identity, row
  index and defaults. **Verified (C):** the accessor declarations and vtable
  offsets; that a per-object substitution of exactly these two hashes is
  implemented and compiled in the sibling mod; that a per-battle-object param
  store exists at `accessor+0x2758` and lists neither parameter; that the
  framework's own registration is per kind.
- **Unverified (D):** whether the engine reads these parameters through that
  accessor at all; how often; what the cache is and when it is rebuilt; what
  stock loss, respawn or destruction does to them; any safe value range; that a
  per-object gate could ever key on saved-Mii identity.
- **Blocker:** per-instance scoping is not demonstrable from available sources.
  Smallest question that would settle it is in §7; it is answerable offline from
  the local 13.0.4 `main` without a console, and it should be the next task.