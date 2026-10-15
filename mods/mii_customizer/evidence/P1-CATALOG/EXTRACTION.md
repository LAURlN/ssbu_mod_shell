# P1-CATALOG - extraction record

Task: P1-CATALOG (Gunner move slots and stat inputs). Worker: Space Bunny Alpha.
Date: 2026-10-04. All commands run from the workspace root in Git Bash.

## Source archive

| item | value |
|---|---|
| archive | `gamedata/ssbu-13.0.4/data.arc` |
| size | 17,600,869,448 B |
| sha256 | `ef615e671e1d4907f0a707f2eb13e3cb0c8539c4e67ac51c89ef547c22b82995` |
| provenance | `gamedata/ssbu-13.0.4/data.arc.provenance.json` (patched 13.0.4, complete) |
| path index | `mods/ssbu_mod_new/dumps/decoded/arc_files.tsv` (590,711 paths) |

No files were read from `dump/` or from the user's ArcExplorer export for this task.

## Tool

`tools/arc-extract/target/release/arc-extract.exe` (`tools/arc-extract/README.md`, status
`working`). No new tool was created and no dependency installed.

## Command 1 - main inputs

```
tools/arc-extract/target/release/arc-extract.exe --arc gamedata/ssbu-13.0.4/data.arc \
  --out gamedata/mii_customizer/P1-CATALOG/files \
  fighter/miigunner/motion/body/c00/motion_list.bin \
  fighter/miigunner/param/vl.prc \
  fighter/miigunner/ai/param/attack_list_param.prc \
  fighter/miigunner/ai/param/attack_data_param.prc \
  fighter/common/param/battle_object.prc \
  fighter/common/param/fighter_param.prc \
  fighter/common/param/common.prc
```

Output (`bytes  sha256  arc path`), exit 0, `7 extracted, 0 failed`:

```
13293   02f2a3250a6383da3739a7c04a959299b39923d29560786139e5b1e81efb7877  fighter/common/param/battle_object.prc
16411   98d98b629be9a19f2b8b3afe33118088faf170d656856b6b4937d35ceaf104e2  fighter/common/param/common.prc
176604  87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2  fighter/common/param/fighter_param.prc
7748    6c0c6b119f586d2806bbc40475fc11aca205131aa13883cf86c5e38783c77011  fighter/miigunner/ai/param/attack_data_param.prc
12012   24109e4ba4f643b2c15b6176f28e1018cc40ba40e1d57f482c052e1c9ed06eae  fighter/miigunner/ai/param/attack_list_param.prc
46272   2b7ed9b6b17a6ab39cc0e6db5121b668d2de44728ac50e9051816612c7d3f4ba  fighter/miigunner/motion/body/c00/motion_list.bin
10192   c3600293023f7098de6e7d6e2795dfe9b9948502d0390bc0f30982e92f3bcd27  fighter/miigunner/param/vl.prc
```

`fighter/common/param/fighter_param.prc` sha256 `87fcf45c...` is the same file the
reference mod already pins in `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_spin_params.rs`
(its header names that hash), which is an independent cross-check that this
extraction is the byte-identical copy.

## Command 2 - helper/weapon motion lists (14 small files, no animations)

```
tools/arc-extract/target/release/arc-extract.exe --arc gamedata/ssbu-13.0.4/data.arc \
  --out gamedata/mii_customizer/P1-CATALOG/files \
  --index mods/ssbu_mod_new/dumps/decoded/arc_files.tsv \
  "fighter/miigunner/motion/gunnercharge/c00/motion_list.bin" \
  "fighter/miigunner/motion/laser/c00/motion_list.bin" \
  "fighter/miigunner/motion/fullthrottle/c00/motion_list.bin" \
  "fighter/miigunner/motion/miimissile/c00/motion_list.bin" \
  "fighter/miigunner/motion/supermissile/c00/motion_list.bin" \
  "fighter/miigunner/motion/groundbomb/c00/motion_list.bin" \
  "fighter/miigunner/motion/stealthbomb/c00/motion_list.bin" \
  "fighter/miigunner/motion/stealthbomb_s/c00/motion_list.bin" \
  "fighter/miigunner/motion/bottomshoot/c00/motion_list.bin" \
  "fighter/miigunner/motion/grenadelauncher/c00/motion_list.bin" \
  "fighter/miigunner/motion/flamepillar/c00/motion_list.bin" \
  "fighter/miigunner/motion/rapidshot_bullet/c00/motion_list.bin" \
  "fighter/miigunner/motion/attackairf_bullet/c00/motion_list.bin" \
  "fighter/miigunner/motion/hat/c00/motion_list.bin"
```

Exit 0, `14 extracted, 0 failed`:

```
64    69782c4b54e90ac4385fae61f1bec5cbc1b53e1ee585a523a889b97d43d181be  motion/attackairf_bullet/c00/motion_list.bin
64    52da2806a4ee0c5f695a46d70ebfb81b232557bb63639c111c174ffe62be373a  motion/bottomshoot/c00/motion_list.bin
104   56017ccd86f56caade1b04fd6239daa58c3cfc564032bd9232aee6d7ef33d7e6  motion/flamepillar/c00/motion_list.bin
284   a8a970808a2954e75cada4d69ea5d13068b9969b71a2bf606811c41eafb7e7e7  motion/fullthrottle/c00/motion_list.bin
104   a51af53568f21473bbbe69e3605954d55051e2de5f826debfa2341fec8c05e4c  motion/grenadelauncher/c00/motion_list.bin
144   2764e1b990dc28b8ed0d557bbd30b37ba0aa1b3efec868b6cdbb1cc248a1d355  motion/groundbomb/c00/motion_list.bin
104   91f314cb5d49505ed9be01fac61cf4983375101dc9777947cc61b77d1776d79c  motion/gunnercharge/c00/motion_list.bin
64    41791da147597eae0714e4fbcea3407b4861621a95c71cda6f9773fe706aaa72  motion/hat/c00/motion_list.bin
104   91f314cb5d49505ed9be01fac61cf4983375101dc9777947cc61b77d1776d79c  motion/laser/c00/motion_list.bin
104   5bb9940f8a711abc38028defa7066ba295de920057cae5235ee0d7fbb99c1431  motion/miimissile/c00/motion_list.bin
184   803104d0f9baf5f12b3e9c64f12ca45e4c1f014bdc21b4026013e0a618bcc735  motion/rapidshot_bullet/c00/motion_list.bin
104   d26a008bdc80f61c38dff2c90d54b0a147a4acd05b817557757d20a8d5b03aff  motion/stealthbomb/c00/motion_list.bin
64    ec40276e9262748a5c29e71e8923361e988407dd5855b667af9dc6d24fcd80a4  motion/stealthbomb_s/c00/motion_list.bin
104   de9c0935eecd02a65116577e3a767152d2c8c3e1bb7840e726e21b0431bbe77b  motion/supermissile/c00/motion_list.bin
```

Measured side note: `gunnercharge` and `laser` are byte-identical
(`91f314cb5d49...`). That is an observation about two files, not a claim about
what the game does with them.

## Scratch scripts and their outputs

All under `mods/mii_customizer/scratch/2026-10-04_P1-CATALOG/` (disposable; they read
only from the mod repo's tools and from the extracted files above).

| script | output (evidence/) |
|---|---|
| `dump_motion_list.py` | `gunner_body_c00_motion_list.json` |
| `resolve_slots.py` | `gunner_body_c00_motion_list_resolved.json`, `gunner_body_c00_slots.txt` |
| `dump_params.py` | `gunner_vl_prc_labelled.tsv`, `fighter_common_param_fighter_param_labelled.tsv`, `fighter_common_param_common_labelled.tsv`, `fighter_common_param_battle_object_labelled.tsv`, `fighter_miigunner_ai_param_attack_list_param_labelled.tsv` |
| (inline awk/python) | `gunner_fighter_param_row82.tsv`, `gunner_stat_candidates.tsv` |

Re-run, from the workspace root:

```
python mods/mii_customizer/scratch/2026-10-04_P1-CATALOG/dump_motion_list.py \
  gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/motion/body/c00/motion_list.bin \
  > mods/mii_customizer/evidence/P1-CATALOG/gunner_body_c00_motion_list.json
python mods/mii_customizer/scratch/2026-10-04_P1-CATALOG/resolve_slots.py \
  > mods/mii_customizer/evidence/P1-CATALOG/gunner_body_c00_slots.txt
python mods/mii_customizer/scratch/2026-10-04_P1-CATALOG/dump_params.py \
  gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/param/vl.prc \
  > mods/mii_customizer/evidence/P1-CATALOG/gunner_vl_prc_labelled.tsv
python mods/mii_customizer/scratch/2026-10-04_P1-CATALOG/dump_params.py \
  gamedata/mii_customizer/P1-CATALOG/files/fighter/common/param/fighter_param.prc \
  > mods/mii_customizer/evidence/P1-CATALOG/fighter_common_param_fighter_param_labelled.tsv
```

## Round-trip and cross-checks that passed

- `motion_list.bin`: `mlist.encode(parse(x)) == x` for all 15 motion lists read.
- Every animation hash in the Gunner body list resolved to a real ARC path
  (0 unresolved of 774 entries).
- Every `param` key hash printed as `name#hash` in the stat tables equals
  `hash40(name)` recomputed from the name (23/23 in `gunner_stat_candidates.tsv`).
- Gunner `fighter_param` row identity: row 82 carries
  `fighter_kind == fighter_kind_miigunner`; rows 80/81/91/92/93 are
  `miifighter` / `miiswordsman` / `miienemyf` / `miienemys` / `miienemyg`.