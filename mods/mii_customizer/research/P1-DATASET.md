# P1-DATASET - reproducible Gunner catalogue for the editor

Task: `P1-DATASET`. Worker: Space Bunny Alpha. Date: 2026-10-04.
Prompt: `prompts/P1-DATASET.md`. Phase: `phases/01_discovery.md`.

Goal of this document: a machine-readable, checked catalogue of Gunner move
slots and numerical stat candidates, generated **from the pinned binaries** so a
later UI can consume it as input data. It is **not** a save schema, **not** a
loadout format, **not** a runtime implementation and **not** a move port.

Evidence tiers: **B** = measured offline from local binaries by scripts that
still exist. **No A** - nothing was run on a console or in an emulator.

Paths are workspace-relative. Inputs, hashes and commands:
`evidence/P1-DATASET/PROVENANCE.md`. Tool and checks:
`tools/gunner-catalog/` (`README.md` there describes the output shape).

---

## 1. What was built

| artefact | what it is |
|---|---|
| `tools/gunner-catalog/build_catalog.py` | stdlib-only generator; recomputes the catalogue from the two binaries on every run |
| `tools/gunner-catalog/validate_catalog.py` | 42 checks over the emitted catalogue, re-derived from the binaries, incl. negative controls; exit 0 required |
| `tools/gunner-catalog/README.md` | purpose, usage, output contract, status |
| `evidence/P1-DATASET/gunner_catalog.json` | `format_version` 1.0.0, 297564 bytes, sha256 `e210923b7a912b760b3f5f76322640562c799a1c2042a55eeaf756e889a81081` |
| `evidence/P1-DATASET/validation_report.txt` | full check output, 42 checks, 0 failed, exit 0 |
| `evidence/P1-DATASET/PROVENANCE.md` | inputs, hashes, commands, and how to read the numbers honestly |

The generator **recomputes** everything from the binaries: motion kinds, script
hashes, animation joins, flags, timing bytes, row identity and stat defaults.
No prose table was serialised. The shared readers
(`mods/ssbu_mod_new/src/pgwr/tools/{mlist,prc}.py`) are imported read-only by
path and were not modified. Nothing was extracted or installed.

## 2. Input provenance

| role | path | sha256 |
|---|---|---|
| Gunner body motion list (774 entries) | `gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/motion/body/c00/motion_list.bin` | `2b7ed9b6b17a6ab39cc0e6db5121b668d2de44728ac50e9051816612c7d3f4ba` |
| common fighter params | `gamedata/mii_customizer/P1-CATALOG/files/fighter/common/param/fighter_param.prc` | `87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2` |

Both were extracted earlier by `P1-CATALOG` and are the same files the
coordinator hashed independently on 2026-10-04. The JSON also records, with full
hashes, the two name dictionaries (`ParamLabels.csv`, `arc_files.tsv`) and the
14 helper motion lists, so every name in the catalogue is traceable to a
dictionary that is itself pinned.

## 3. The catalogue

### 3.1 Stable identifiers for user actions

23 slots, 31 choices, 104 motion states. `B`.

| group | slots |
|---|---|
| normal | `normal_jab` (one ordered 3-stage chain), `normal_dash` |
| tilts | `tilt_up`, `tilt_side`, `tilt_down` |
| smashes | `smash_forward`, `smash_up`, `smash_down` (each a release + charge-hold state pair) |
| aerials | `aerial_neutral`, `aerial_forward`, `aerial_back`, `aerial_up`, `aerial_down` |
| grab | `grab` (six states), `pummel` |
| throws | `throw_forward`, `throw_back`, `throw_up`, `throw_down` |
| specials | `special_neutral`, `special_side`, `special_up`, `special_down` - **three existing alternatives each** |

Every non-special slot has exactly one available choice, because Gunner ships one
move for it; each special direction has the three alternatives already in the
file. **This is a provisional editor grouping, not proof of native routing.**
Every slot carries `grouping_status: PROVISIONAL_EDITOR_GROUPING` and a note
saying exactly that.

**Jab stays in the sequence.** `normal_jab` is a single slot with a single choice
carrying `sequence_constraint: ordered` and stages `stage_1`, `stage_2`,
`stage_3` (`attack_11/12/13`). No stage is offered as an independent attack and
the stages are not mixable. The stage order is the authored order in this file;
that is not proof of the engine's chain order, and the JSON says so.

### 3.2 What each state carries

Per state, all recomputed from the binary:

* `entry_index`, `kind_hash`, `kind_name` (+ `kind_hash_matches_name`),
  `status`;
* `game_script` = hash, name, `name_source`, `name_verified`;
* `flags_raw_u16` / `flags_raw_hex` and `blend_raw_u8`, raw as authored;
* `animations` = per-clip hash, basename and full ARC path(s) - the basename join
  can collide across motion folders, so all candidate paths are kept;
* `timing_raw` = the four separate tail bytes with their offsets
  (`xlu_start` 24, `xlu_end` 25, `cancel_frame` 26, `no_stop_intp` 27), the
  packed `cancel_u16_raw`, the `0x100` bit, and an internal consistency check.

The timing block is explicitly labelled **authored bytes, not runtime frame
promises**, with the evidence for the field semantics (P1-CATALOG-AUDIT against
the decoded GameWatch reference, 746/746 per offset).

**Display names** are plain English author labels authored in the generator,
carrying `label_origin: author_display_label` and `is_game_string: false`. They
are never presented as the game's own strings.

### 3.3 Unknowns kept explicit

100 of 104 states have a label-table name; **4 do not** and are stored by kind
hash plus the clip they point at, with `status: UNKNOWN_KIND_NAME_BY_HASH`:

| kind hash | clip | what it is |
|---|---|---|
| `0x12772b6b5f` | `d00specialairn2end.nuanmb` | neutral special option 2, air end state |
| `0x0d3aaf0366` | `d02specialhi3f.nuanmb` | up special option 3, forward directional variant |
| `0x0d3dc2c77f` | `d02specialhi3b.nuanmb` | up special option 3, back directional variant |
| `0x15eba8646e` | `d02specialairhi3start.nuanmb` | up special option 3, air start state |

None of these is guessed into a label. Each has its own machine-readable
`coverage_gaps` entry that names the exact slot/choice/role that consumes it.

100 of 104 states carry a **hash-verified** game-script name. Names are generated
as candidate forms (`game_` + separators dropped, trailing `_s` dropped,
`_hold` -> `charge`, `_l` -> its base state) and are accepted **only** when
`hash40(candidate)` equals the entry's own script field, so a wrong rule fails
loudly instead of inventing a name. The 4 unnamed states keep their script hash
with `name: null`.

File-wide, 303 of 774 kinds have no label-table name. That is higher than
P1-CATALOG's 202 because this generator uses the label table only and does not
repeat that task's fixed-list and clip-stem passes - a difference of method, not
a contradiction, and no claim is made about the smaller set.

### 3.4 Dependencies, honestly empty where they are

* Aerial slots declare their paired `landing_air_*` state as a dependency
  (`role: paired_landing`), so replacing an aerial flags the landing entry.
* Throws note that a victim-side reaction entry exists; those victim entries are
  not catalogued as slots.
* The 14 helper motion lists are listed as `dependency_candidates` with
  `link_status: UNLINKED` and an empty `linked_slots`. **No special choice
  claims a helper, script or projectile.** The link lives in script/article code
  that is not in the local inputs, so it was not asserted. A validation check
  fails if a helper reference ever appears inside a special choice.

## 4. Stat candidates

The twelve candidates from P1-CATALOG §7, re-decoded from
`fighter_param.prc` -> `fighter_param_table[82]`:

| parameter | hash | type | default (exact decode) | f32 bits |
|---|---|---|---|---|
| `weight` | `0x0607cd5541` | float | 104.0 | `0x42d00000` |
| `scale` | `0x05ec462584` | float | 1.149999976158142 | `0x3f933333` |
| `walk_speed_max` | `0x0ee2ec2860` | float | 1.0 | `0x3f800000` |
| `run_speed_max` | `0x0d5aaabf9b` | float | 1.3700000047683716 | `0x3faf5c29` |
| `dash_speed` | `0x0adec47ea3` | float | 1.6299999952316284 | `0x3fd0a3d7` |
| `air_speed_x_stable` | `0x1220fc2660` | float | 0.9300000071525574 | `0x3f6e147b` |
| `air_speed_y_stable` | `0x12ec5626fe` | float | 1.4500000476837158 | `0x3fb9999a` |
| `air_accel_y` | `0x0ba18057d9` | float | 0.09799999743700027 | `0x3dc8b439` |
| `air_accel_x_mul` | `0x0f71f4d4f8` | float | 0.0430000014603138 | `0x3d3020c5` |
| `jump_y` | `0x06a0d82dad` | float | 30.899999618530273 | `0x41f73333` |
| `jump_speed_x` | `0x0cc9d2f2da` | float | 0.949999988079071 | `0x3f733333` |
| `jump_count_max` | `0x0e35ca3d82` | i32 | 2 | - |

The rounded values in `P1-CATALOG` §7 are the same numbers; the JSON keeps the
exact `f32` decode plus its bit pattern so a byte-level check is possible later.

Each record carries the decoded type, the expected type, the exact `f32` bits,
the parameter hash with `hash_verified`, and the row it came from. Row identity is
measured, not assumed: the row key `fighter_kind` (`0x0c541ef0b2`) equals
`hash40("fighter_kind_miigunner")` (`0x166e9fae70`) in **exactly one** of 94 rows,
and that index (82) is what every stat record points at.

**Safe ranges: `UNKNOWN`, with `min`/`max` null.** No range was measured and none
is inferred.

**Runtime override** is *supported by the schema*, not claimed to work: each stat
has `runtime_override.schema_supported: true`, `declared_candidate: true`,
`observed: false`, `mechanism: UNKNOWN`, `per_instance_scope: UNKNOWN`. Nothing
here shows the engine reads row 82 unchanged, or that one saved Mii can be scoped
to one battle object.

**No cross-stat independence is claimed.** `cross_stat_relationships.status` is
`UNKNOWN` and `independent_of_other_stats` is `null` for every stat, with a note
that a row may hold related keys (e.g. `jump_y` and `jump_initial_y`) whose
relationship was not measured. Nine measured neighbour keys in the same row are
recorded under `stat_row_neighbours`, flagged `in_candidate_set: false`.

## 5. Validation actually run

`python -B mods/mii_customizer/tools/gunner-catalog/validate_catalog.py` ->
**42 checks, 0 failed, exit 0** (full output: `evidence/P1-DATASET/validation_report.txt`).

1. **Determinism** - three rebuilds under `PYTHONHASHSEED` 0 / 1 / 12345 are
   byte-identical and equal the committed file (`e210923b7a91...`).
2. **Identifiers** - slot ids and choice ids unique; exactly five aerial slots;
   one choice per normal, three per special direction; four special directions;
   jab is one ordered three-stage chain; no pending-scope group is offered.
3. **Hash joins** - every resolved kind name, every named game script and every
   named clip re-hashes to the hash stored beside it; the 4 unresolved names are
   explicit.
4. **Stats** - twelve candidates; row identity unique and recorded; kind hash
   equals `hash40(fighter_kind_miigunner)`; parameter hashes recomputed; decoded
   types match the file; **defaults re-read from the `.prc`**; every safe range
   UNKNOWN with null bounds; override declared but not observed; no independence
   claimed.
5. **Byte-field separation, including the reported 334 / 318 entries.** For
   `attack_s4_s`: `cancel_u16_raw=334`, tail bytes `00 00 4e 01`, so
   `cancel_frame=78` and `no_stop_intp=1`; zeroing the `no_stop_intp` byte *in
   memory* leaves the frame byte at 78 and recomputes the raw `u16` to 78 - the
   two fields are separate bytes. For `attack_air_hi`: raw `318`, bytes
   `00 00 3e 01`, `cancel_frame=62`, `no_stop_intp=1`. The old reading is also
   shown to be wrong on its own terms (raw `u16` != frame count for both).
6. **Scope** - the four pending-scope gaps exist; no recovery/landing motion is
   sold as an attack and the five `landing_air_*` states appear only as aerial
   dependencies; specials claim no helper closure; every unresolved name has a
   gap; no absolute machine path in the JSON; the "not a move port" disclaimer
   and provisional grouping are present; all display labels are marked as author
   labels.
7. **Negative controls** (each must fail loudly):
   * wrong input hash in provenance -> rejected;
   * a second wrong provenance hash -> rejected; real provenance -> accepted;
   * plausible-but-wrong known reference (`attack_12` on the `attack_11` hash) ->
     caught by the join check;
   * a dropped name marked resolved -> not counted as resolved;
   * an altered stat default -> differs from the file;
   * a copy with one aerial removed (4 aerials) -> does not satisfy the
     five-aerial check.

## 6. Kept pending, not silently dropped

Machine-readable in `coverage_gaps` (18 entries):

* **Final Smash** (`gap_final_smash`) - kinds exist and are named; scope is a
  coordinator decision. The `d04final*` naming trap (the Full Throttle helper
  folder owns clips with the same names) is restated in the gap text.
* **Get-up attacks** (`gap_get_up`) - kinds exist; scope undecided. **Recovery and
  movement states are not enumerated as get-up attacks**: no `down_attack_*`,
  `down_stand`, `down_bounce`, walk/fall/jump state appears in any slot, and a
  check enforces that.
* **Ledge / cliff** and **taunts** - present in the file, scope undecided.
* **Unlinked helper links**, **missing script bodies**, **stat ranges**,
  **`c06`/`c07` unread**, **`vl.prc` per-move `hit_data` unmined**, **no runtime
  evidence**, **back-tilt routing**, **`no_stop_intp` runtime meaning**, and
  **identity/persistence ownership**.

## 7. Limitations

1. **No tier A evidence.** No console, no emulator, no build. Every value is
   file-level. Nothing here shows the game reads these values in a match.
2. **Slot grouping is a proposal.** The motion list does not say which button
   reaches which kind; the audit's control file settles field meaning, not input
   routing. Back tilt is unresolved.
3. **Timing semantics are inherited across fighters.** `cancel_frame` /
   `no_stop_intp` / `xlu_*` were validated on GameWatch body c00 and applied to
   Gunner on identical layout. That is `B` by inference, not a second decode.
4. **Only `body/c00` was read.** `c06`/`c07` exist; one script per slot per
   costume set is not established.
5. **Script bodies are absent.** No hit box, damage, helper or behaviour claim.
6. **Names come from dictionaries.** Kind names are a label-table join, script
   names are hash-verified form candidates, clip names are a basename hash join.
   None of these is the game's own on-screen move naming.
7. **Untouched by design:** saved-Mii identity, save format, loadout
   persistence, native UI binding (other tasks' lanes). This catalogue is input
   data for them, not an integration.

## 8. Suggested next step

Small and cheap: **decode `fighter/miigunner/motion/body/c06/motion_list.bin`**
(already extracted alongside c00) and re-run this generator with it as an extra
input. That closes limitation 4 with one existing file and one extra hash, and
would show whether the 23 slot identifiers are stable across a costume set -
which is exactly the assumption a slot-based UI would lean on.

Escalation to a premium model is **not** requested. Nothing found here needs
native RE; the open items need measurements or script bodies.

---

## Summary

- **P1-DATASET: DONE.**
- **Changed files** (all inside this task's exclusive write paths):
  - `mods/mii_customizer/tools/gunner-catalog/build_catalog.py`
  - `mods/mii_customizer/tools/gunner-catalog/validate_catalog.py`
  - `mods/mii_customizer/tools/gunner-catalog/README.md`
  - `mods/mii_customizer/evidence/P1-DATASET/gunner_catalog.json`
  - `mods/mii_customizer/evidence/P1-DATASET/validation_report.txt`
  - `mods/mii_customizer/evidence/P1-DATASET/PROVENANCE.md`
  - `mods/mii_customizer/research/P1-DATASET.md` (this report)
  - `mods/mii_customizer/scratch/2026-10-04_P1-DATASET/` (5 disposable probe
    scripts used while locating the tail byte offsets and the row-82 identity:
    `probe_prc.py`, `probe_prc2.py`, `probe_specials.py`, `probe2.py`,
    `probe3.py`)
- **No new extraction, no dependency installed, no Lua/layout/identity/shared
  contract touched.** The shared readers were imported read-only; `STATUS.md`,
  `CHANGELOG.md`, `CURRENT_INSTALL.md` and other tasks' reports were not edited.
- **Observed checks:** 42/42 validator checks pass, exit 0; determinism across
  three `PYTHONHASHSEED` values; 100/104 state names resolved with the 4
  unknowns retained; 100/104 script names hash-verified; 12/12 stat hashes,
  types and defaults re-derived from the `.prc`; Gunner row unique (82 of 94);
  334/318 byte separation proved by in-memory byte perturbation; 7 negative
  controls all behave as required.
- **Unverified (D / not established):** native input routing for any slot; which
  helper or script each special alternative uses; runtime reading of row 82;
  any safe range, override mechanism or per-instance scope; `no_stop_intp` at
  runtime; back-tilt routing; the 4 unnamed kinds; Final Smash / get-up / ledge /
  taunt scope; `c06`/`c07` layout; per-move `hit_data`.
- **Blockers:** none. Nothing in this task requires the console or a premium
  model.
