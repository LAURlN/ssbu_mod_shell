# gunner-catalog

Generates and validates the machine-readable Gunner move/stat catalogue that the
Mii Customizer editor will read as **input data**. Built for task `P1-DATASET`.

Status: **working** (offline). Evidence tier **B** — everything is measured from
pinned local binaries. No console, no emulator, no runtime behaviour is claimed.

## What it is not

* Not a save schema, not a loadout format, not a persistence design.
* Not a move port. Nothing here shows any move working in a match.
* Not a statement about native input routing. The slot grouping is a **provisional
  editor grouping** built from motion kinds and hashes.
* It does not read saved-Mii identity, the save format or the native editor.

## Files

| file | role |
|---|---|
| `build_catalog.py` | recomputes `evidence/P1-DATASET/gunner_catalog.json` from the pinned binaries |
| `validate_catalog.py` | re-derives and checks the emitted catalogue (42 checks incl. negative controls); also the smoke check |

Both are stdlib-only Python 3. They import the shared readers
`mods/ssbu_mod_new/src/pgwr/tools/mlist.py` and `.../prc.py` **read-only by path**
and never modify them.

## Usage

From the workspace root:

```sh
# generate
python -B mods/mii_customizer/tools/gunner-catalog/build_catalog.py \
    --out mods/mii_customizer/evidence/P1-DATASET/gunner_catalog.json

# smoke check / validation (exit 0 = every check passed)
python -B mods/mii_customizer/tools/gunner-catalog/validate_catalog.py
```

Optional arguments (all default to the workspace layout, relative paths only):

```
--motion-list    gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/motion/body/c00/motion_list.bin
--fighter-param  gamedata/mii_customizer/P1-CATALOG/files/fighter/common/param/fighter_param.prc
--labels         mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv        (name dictionary only)
--arc-index      mods/ssbu_mod_new/dumps/decoded/arc_files.tsv          (animation hash -> ARC path)
--helper-root    gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/motion
```

Pinned input hashes (verified on every validator run, and recorded in the
catalogue's `inputs` block):

* `motion_list.bin` sha256 `2b7ed9b6b17a6ab39cc0e6db5121b668d2de44728ac50e9051816612c7d3f4ba`
* `fighter_param.prc` sha256 `87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2`

Both were extracted earlier by `tools/arc-extract`; see
`evidence/P1-CATALOG/EXTRACTION.md`. This tool extracts nothing and installs nothing.

## Output shape

`gunner_catalog.json`, `format_version` 1.0.0:

| key | content |
|---|---|
| `inputs` | role, relative path, ARC path, full sha256 and byte size of every input |
| `fighter_identity` | `fighter_param_table` row 82, identified by `fighter_kind == hash40(fighter_kind_miigunner)` (unique in the file) |
| `editor_slots` | 23 slots: jab chain, dash attack, 3 tilts, 3 smashes, 5 aerials, grab family, pummel, 4 throws, 4 special directions |
| `stat_candidates` | the twelve numerical candidates with decoded type, default, f32 bits, hash, and explicit UNKNOWN ranges |
| `stat_row_neighbours` | measured neighbours in the same row, flagged as not proposed stats |
| `dependency_candidates` | 14 helper motion lists, `link_status: UNLINKED` |
| `coverage_gaps` | machine-readable unknowns and pending-scope items |
| `explicit_unknowns` | the short list of things this file does not know |

Rules baked into the generator:

* **Jab stays a chain.** `normal_jab` is one slot with one choice carrying
  `sequence_constraint: ordered` and stages `stage_1..3`; the stages are never
  offered as independent attacks.
* **One choice per normal, three per special direction.** Those are the choices
  Gunner already ships.
* **Raw authored data stays raw.** Flags, blend and the four separate timing
  bytes (`xlu_start`, `xlu_end`, `cancel_frame`, `no_stop_intp`) are stored with
  their byte offsets plus the packed `u16`, and labelled as authored bytes, not
  runtime frame promises.
* **Unknowns stay unknown.** A kind with no name is stored by hash + clip with
  `status: UNKNOWN_KIND_NAME`; four such states exist and each has a gap record.
* **Names are hash-verified.** A kind/script/clip name is only emitted when
  `hash40(name)` equals the hash stored beside it. Game-script names are
  generated as candidate forms (`game_` + separators dropped, `_s` dropped,
  `_hold` -> `charge`, `_l` -> base state) and accepted only on a hash match, so
  a wrong rule fails loudly instead of inventing a name.
* **No invented dependency closure.** Helper motion lists are listed as unlinked
  candidates; no special choice claims a helper, script or projectile.
* **Display labels are author labels.** Every `display_label` carries
  `label_origin: author_display_label` and `is_game_string: false`.
* **Pending scope offers nothing.** Final Smash, get-up, ledge and taunts appear
  as `PENDING_SCOPE` gaps only. Recovery and landing motions are never sold as
  attacks; the five `landing_air_*` states appear solely as declared aerial
  dependencies.

## Validation

`validate_catalog.py` re-derives everything from the binaries:

1. determinism — three rebuilds under different `PYTHONHASHSEED` values are
   byte-identical and equal the committed file;
2. identifiers — unique slot/choice ids, exactly five aerial slots, one choice
   per normal, three per special, jab as one ordered chain;
3. hash joins — every resolved kind, named script and named clip re-hashes to
   its stored hash;
4. statistics — twelve candidates, re-read types and defaults from the `.prc`,
   `hash40` recomputed per key, unique Gunner row, every safe range UNKNOWN, no
   cross-stat independence, runtime override declared but not claimed observed;
5. byte separation — the reported 334 / 318 entries are re-read byte-wise: the
   raw `u16` differs from `cancel_frame` (78 / 62), `no_stop_intp` is a separate
   byte, and zeroing that byte in memory leaves the frame byte untouched;
6. scope — pending-scope gaps exist, recovery motions are not attacks, specials
   claim no helper closure, gaps are machine-readable, no absolute paths, no
   "complete move port" claim;
7. negative controls — a wrong input hash is rejected, a plausible-but-wrong
   known reference (`attack_12` on the `attack_11` hash) is rejected, a dropped
   name is not counted as resolved, an altered stat default differs from the
   file, and a four-aerial copy does not satisfy the five-aerial check.

Exit code 0 only when all checks pass.
