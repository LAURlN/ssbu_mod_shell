"""Which G&W body meshes does G&W's own clip set never animate?

The hammer turned out to be driven by native code rather than by a visibility
group or a clip track: `RHammerM` is in `model.numshb`, no clip names it, and
`rhand_hammer` is not a state in `param_visibility_data_body`. That combination -
present in the model, absent from every track, absent from the table - is a
reliable fingerprint for "his native logic shows this mesh directly", which is a
different fix from both the article route and the R22 group route.

This tool lists that set, so any remaining prop can be classified from data
before anyone writes code. Run it against the ORIGINAL export, not the built mod,
because `complete_visibility` deliberately writes tracks for all 98 meshes and
would hide the very set we are looking for.

    toolchains/py312/python.exe src/pgwr/tools/untracked_meshes.py
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import ssbh_data_py as s  # noqa: E402  (vendored; needs the cp312 python, see build.py)

EXPORT = Path(__file__).resolve().parents[3] / 'dumps' / 'arc'

# Layers are partial overlays on the body clip; a mesh that only a layer names is
# still "untracked" for the body clips, but the layer is worth reporting on its own.
LAYER_PREFIX = 'a00itemhand'


def main() -> int:
    slot = sys.argv[1] if len(sys.argv) > 1 else 'c06'
    gw_slot = sys.argv[2] if len(sys.argv) > 2 else slot
    model_dir = EXPORT / 'fighter/gamewatch/model/body' / gw_slot
    motion_dir = EXPORT / 'fighter/gamewatch/motion/body' / gw_slot

    mesh = s.mesh_data.read_mesh(str(model_dir / 'model.numshb'))
    meshes = sorted({o.name.split('_VIS_')[0] for o in mesh.objects})
    print(f'G&W {gw_slot}: {len(meshes)} distinct body meshes in model.numshb\n')

    # Which clip names each mesh, and with what on/off values.
    naming: dict[str, set[str]] = defaultdict(set)
    always_on: dict[str, int] = defaultdict(int)
    clips = 0
    for path in sorted(motion_dir.glob('*.nuanmb')):
        anim = s.anim_data.read_anim(str(path))
        clips += 1
        for g in anim.groups:
            if g.group_type.name != 'Visibility':
                continue
            for n in g.nodes:
                naming[n.name].add(path.name)
                vals = n.tracks[0].values if n.tracks else []
                if vals and all(v is True for v in vals):
                    always_on[n.name] += 1

    untracked = [m for m in meshes if m not in naming]
    tracked_nowhere = [m for m in meshes if m not in naming and not always_on.get(m)]

    print(f'{clips} clips scanned.\n')
    print(f'=== UNTRACKED in every clip ({len(untracked)}) ===')
    for m in untracked:
        print(f'  {m}')
    if not untracked:
        print('  (none - every mesh has a track somewhere)')

    print(f'\n=== untracked AND never a layer-only name ({len(tracked_nowhere)}) ===')
    for m in tracked_nowhere:
        print(f'  {m}')

    print('\n=== mesh names a clip tracks that are NOT in the model ===')
    for name in sorted(set(naming) - set(meshes)):
        print(f'  {name}   ({len(naming[name])} clips)')

    print('\n=== meshes that are ON for every clip that touches them ===')
    for name in sorted(always_on):
        tag = '' if name in meshes else '   [NOT IN MODEL]'
        print(f'  {name}: {always_on[name]}/{len(naming[name])} clips on{tag}')

    # A clip that only ever shows one mesh is the article-style "prop is drawn
    # here" case, and is worth seeing separately.
    print('\n=== layer-only names (a00itemhand) ===')
    for name in sorted(n for n in naming if n.startswith('a00itemhand') or
                       any(c.startswith(LAYER_PREFIX) for c in naming[n])):
        if not any(c.startswith(LAYER_PREFIX) for c in naming[name]):
            continue
        print(f'  {name}: {sorted(naming[name])}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
