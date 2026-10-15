# P1-CATALOG-AUDIT - inputs, commands and controls

Task: P1-CATALOG-AUDIT. Date: 2026-10-04. Evidence tier **B** (measured offline
by the scripts listed here, which are kept in
`mods/mii_customizer/scratch/2026-10-04_P1-CATALOG-AUDIT/`).

## Inputs

No new extraction was needed. Every binary this task reads was already present from
P1-CATALOG or the existing 13.0.4 file tree, and both were read read-only.

| input | sha256 | origin |
|---|---|---|
| `gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/motion/body/c00/motion_list.bin` | `2b7ed9b6b17a6ab39cc0e6db5121b668d2de44728ac50e9051816612c7d3f4ba` | P1-CATALOG; hash independently re-verified by this task and it matches the coordinator's 2026-10-04 check |
| `gamedata/ssbu-13.0.4/files/fighter/gamewatch/motion/body/c00/motion_list.bin` | `306be009edb40b692f58aa67eb2bb18c12e47068d8350d4e0a7e96ceb88ed0a2` | existing 13.0.4 extraction; used as the **decoded-field control** |
| `mods/ssbu_mod_new/dumps/scripts/gamewatch_motion_list.yml` | (text reference) | existing decoded field listing for GameWatch body c00 |
| `mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv` | (text reference) | existing hash->name label table |
| `gamedata/mii_customizer/P1-CATALOG/files/fighter/common/param/fighter_param.prc` | `87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2` | reused read-only from P1-CATALOG for the stat-table correction |

Hashes were computed with `sha256sum` inside this task; the two motion-list hashes
are printed at the top and bottom of every script's output.

## Controls

The audit's central control is **GameWatch body c00**, chosen because
`dumps/scripts/gamewatch_motion_list.yml` already names its decoded fields
(`game_script`, `blend_frames`, `xlu_start`, `xlu_end`, `cancel_frame`,
`no_stop_intp`). That makes it possible to check the shared reader's *semantics*
against something other than a round trip. 746 kinds, 0 YAML-only kinds, so the
comparison is closed in both directions.

Two further controls are used:

- **Round trip** `encode(parse(x)) == x`, asserted for both files, to separate
  "bytes preserved" from "fields interpreted correctly". Round trip alone is *not*
  treated as semantic validation.
- **Negative control on the masking test.** If bit `0x100` were simply noise, the
  masked and unmasked readings would both fit somewhere. The test instead uses the
  28 kinds where `xlu_start` / `xlu_end` are non-zero, which are exactly the cases
  that can distinguish a single byte from a `u16` at each tail position.

## Commands run

```
python -B mods/mii_customizer/scratch/2026-10-04_P1-CATALOG-AUDIT/audit_slots_and_timing.py
python -B mods/mii_customizer/scratch/2026-10-04_P1-CATALOG-AUDIT/validate_reader_fullfile.py
python -B mods/mii_customizer/scratch/2026-10-04_P1-CATALOG-AUDIT/adjudicate_cancel_bits.py
python -B mods/mii_customizer/scratch/2026-10-04_P1-CATALOG-AUDIT/pin_tail_layout.py
python -B mods/mii_customizer/scratch/2026-10-04_P1-CATALOG-AUDIT/final_verify.py
python -B mods/mii_customizer/scratch/2026-10-04_P1-CATALOG-AUDIT/check_report_claims.py
python -B mods/mii_customizer/scratch/2026-10-04_P1-CATALOG-AUDIT/verify_catalog_script_names.py
```

Each script imports `mods/ssbu_mod_new/src/pgwr/tools/mlist.py` read-only. No shared
tool, dump, script or production file was modified. `-B` avoids writing `__pycache__`
into the read-only dump tree.

## Evidence files produced

| file | sha256 (of this record's generation) | content |
|---|---|---|
| `reader_vs_gamewatch_decoded_yaml.txt` | `80518df79804a67cadcab8e89d782ccab19af2161949a773436cd1f9e6aa4532` | full-file reader-vs-YAML comparison, 746 kinds |
| `cancel_field_adjudication.txt` | `391c195c5c2f6051ae506f2382f8f84342a2a79b93975021149e1bfaf408f50b` | the `+256` disagreements, the bit-`0x100` test, Gunner outliers re-read |
| `tail_layout_and_variants.txt` | `cb703698a5b62e200fb02caff74ae65f07ae4b5c26885c8e299dda4fcb61122c` | 28-byte tail layout, byte-wise field confirmation, directional-variant comparison |
| `representative_entries_raw.txt` | `0344c63161c18eb926a371bc8bcd61b130071a07a29845f18147aff0485b7575` | raw offsets/bytes and every `u16`/`u32` read for six representative Gunner entries |
| `report_claims_verification.txt` | `c8f78e9794e8051fb399ee9c2daa41f51bb3ccd08eb91ce2d08244262872307d` | every quantitative **B** claim in the report re-derived and asserted; final result **0 failing claims** |
| `catalog_script_name_verification.txt` | `cd914d74357c395755c0175bc1fee10fa020a1d9710f9b3771611ae4ae1bc59f` | all 29 `game_*` names written into the corrected tables re-hashed against their entries' `game_script` field; result **0 failing claims** |

## Verification of the report's own claims

`check_report_claims.py` re-derives every number the report marks **B** directly from
the two binaries: the 18 normal-attack entries, the five landing kinds, the
grab/pummel/throw block, the side-special cancels, the `special_lw1_*` `_l` game-script
equality, the down-attack and `hi2_squat` xlu values, the masked-cancel maximum, the
count of entries with bit `0x100` set, directional-variant presence in both files, the
absence of Gunner motion-kind hashes from the AI TSV, the presence of every
Final Smash / ledge / appeal / get-up kind, both entry counts, both round trips and
both input hashes.

It is a real gate, not a formality: it caught one incorrect claim in an earlier draft
of the report (`down_attack_d` `xlu_end` is **24**, not 23), which was corrected before
publication. Final run: `RESULT: 0 failing claim(s)`.

`verify_catalog_script_names.py` closes the last gap: P1-CATALOG-AUDIT filled in
`game_*` names that had previously been `-`, and a name is only worth anything if
`hash40(name)` equals the entry's own `game_script` field. All **18** normal-attack
script names and all **11** grab/pummel/throw names were re-hashed and match.
A negative control asserts that the plausible-but-wrong forms
(`game_attack_s3_s`, `game_attacks3_s`, `game_attack_s3`, `game_attacks4_s`,
`game_attack_s4_s`) do **not** match `attack_s3_s` or `attack_s4_s`, which is what
pins the naming rule: drop the `_s` suffix and the underscore before the digit, then
prefix `game_` (`attack_s3_s` -> `attacks3` -> `game_attacks3`). Final run:
`RESULT: 0 failing script-name claim(s)`.

## Not done

No extraction into `gamedata/mii_customizer/P1-CATALOG-AUDIT/` was necessary, so that
optional path was not created. No animation, mesh, script body or save data was read.
`dumps/scripts/SSBU-Dumped-Scripts-main` is absent from this workspace, so script
*bodies* remain unavailable and no claim here depends on one.