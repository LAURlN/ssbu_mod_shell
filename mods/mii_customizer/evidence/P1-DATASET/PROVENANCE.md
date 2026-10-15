# P1-DATASET - input provenance and commands

Task: `P1-DATASET` (worker: Space Bunny Alpha, 2026-10-04). Prompt:
`prompts/P1-DATASET.md`. All paths are workspace-relative. Commands were run from
the workspace root in Git Bash with `python -B` (3.12.3, no bytecode written).

**This task performed no extraction, installed nothing, and modified no input.**
The two binaries below were already extracted by `P1-CATALOG`
(`evidence/P1-CATALOG/EXTRACTION.md`) and were read only.

## Binary inputs (pinned, re-hashed on every validator run)

| role | path | sha256 | bytes |
|---|---|---|---|
| Gunner body motion list | `gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/motion/body/c00/motion_list.bin` | `2b7ed9b6b17a6ab39cc0e6db5121b668d2de44728ac50e9051816612c7d3f4ba` | 46272 |
| common fighter params | `gamedata/mii_customizer/P1-CATALOG/files/fighter/common/param/fighter_param.prc` | `87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2` | 176604 |

ARC paths: `fighter/miigunner/motion/body/c00/motion_list.bin` and
`fighter/common/param/fighter_param.prc`, both from
`gamedata/ssbu-13.0.4/data.arc` (13.0.4 patched).

These match the hashes the coordinator independently checked with
`Get-FileHash` on 2026-10-04 (`research/COORDINATOR-2026-10-04.md`).

## Name dictionaries (read-only, no measured value depends on them)

| role | path | sha256 |
|---|---|---|
| motion-kind labels | `mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv` | `6ae7f792609612370e6b9244e1d6986ebd8ced9bbb77fad49de8c568919344f4` |
| archive path index | `mods/ssbu_mod_new/dumps/decoded/arc_files.tsv` | `727a03c518ecb4614e8bca07202e916a9c2f4305f3f63a54b9d21a6db2c26369` |

Both hashes are recomputed and re-stored by the generator on every run, so the
copies in `gunner_catalog.json` -> `inputs.name_dictionaries` are authoritative.

`ParamLabels.csv` supplies names for kind hashes only. `arc_files.tsv` joins an
animation hash (`hash40` of the file **basename**, extension included) to an ARC
path. Neither file is a source for any numeric value.

## Helper motion lists (auxiliary, read-only)

`gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/motion/*/c00/motion_list.bin`
- 14 files, each hashed in `gunner_catalog.json` -> `dependency_candidates`. They
are listed as `link_status: UNLINKED` because nothing in these inputs links a
helper to a slot.

## Commands

Generate:

```sh
python -B mods/mii_customizer/tools/gunner-catalog/build_catalog.py \
  --out mods/mii_customizer/evidence/P1-DATASET/gunner_catalog.json
```

Validate (exit 0 required):

```sh
python -B mods/mii_customizer/tools/gunner-catalog/validate_catalog.py
```

Both commands are recorded with their full output in `validation_report.txt`.

## Outputs

| file | sha256 / size |
|---|---|
| `evidence/P1-DATASET/gunner_catalog.json` | `e210923b7a912b760b3f5f76322640562c799a1c2042a55eeaf756e889a81081`, 297564 bytes |
| `evidence/P1-DATASET/validation_report.txt` | see the file; 42 checks, 0 failed, exit 0 |

## Reading the numbers honestly

* `motion_source.unnamed_entry_count` is **303 of 774**, higher than the 202
  reported by `P1-CATALOG`, because this generator resolves names from the label
  table only and does not repeat that task's fixed-list and clip-stem passes.
  That is a difference of method, not a contradiction: nothing here claims a
  smaller unnamed set.
* Of the 104 motion states the catalogue references, **100 have a name** and 4 are
  explicit unknown-name records (kind hash plus clip):
  `0x12772b6b5f` (`d00specialairn2end`), `0x0d3aaf0366` (`d02specialhi3f`),
  `0x0d3dc2c77f` (`d02specialhi3b`), `0x15eba8646e` (`d02specialairhi3start`).
* 100 of 104 states carry a **hash-verified** game-script name; the 4 unnamed
  states have no script name, and their script hashes are still stored.
* Evidence tier **B** throughout. No tier A. Nothing here is runtime behaviour.
